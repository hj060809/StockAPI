import asyncio
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession

import shared.shared_lib.logger_config  # noqa: F401 — loguru 핸들러 설정 적용
from loguru import logger
from worker.services.action_service import ActionService
from worker.services.candle_service import CandleService, CollectionTask

# Timeframe enum 값 → yfinance interval 매핑
# 미포함 timeframe(4h/12h/3d/2w/6M/1y)은 yfinance 미지원 — 경고 후 skip
# TODO: 추후 1h/1d 데이터를 리샘플링해서 지원하는 확장 포인트
YF_INTERVAL_MAP = {
    '1m': '1m',
    '5m': '5m',
    '15m': '15m',
    '30m': '30m',
    '1h': '60m',
    '1d': '1d',
    '1w': '1wk',
    '1M': '1mo',
    '3M': '3mo',
}

# yfinance intraday 데이터 보존 기간 — 이보다 과거는 요청해도 안 옴
RETENTION_LIMIT = {
    '1m': timedelta(days=30),
    '5m': timedelta(days=60),
    '15m': timedelta(days=60),
    '30m': timedelta(days=60),
    '1h': timedelta(days=730),
}

# 요청당 최대 조회 범위 — 1m은 요청당 8일 제한이라 7일씩 나눠서 요청
REQUEST_CHUNK = {
    '1m': timedelta(days=7),
}

class CandleCaller:
    def __init__(self, db: AsyncSession):
        self.service = CandleService(db)

    async def call(self):
        raise NotImplementedError

class YFinanceCaller(CandleCaller):
    def __init__(
            self,
            db: AsyncSession,
            concurrency: int = 5,
    ):
        super().__init__(db)
        self.action_service = ActionService(db)
        # fetch는 스레드로 병렬화하되 yfinance rate limit 대비 동시성 제한
        self._fetch_sem = asyncio.Semaphore(concurrency)
        # AsyncSession은 동시 사용 불가 — DB 접근은 직렬화
        self._db_lock = asyncio.Lock()

    async def call(self):
        """수집 계획 조회 → 티커별 병렬 fetch → 저장"""
        async with self._db_lock:
            plan = await self.service.get_collection_plan()

        tasks = []
        for task in plan:
            if task.timeframe not in YF_INTERVAL_MAP:
                logger.warning(f"{task.symbol} {task.timeframe}: timeframe not supported by yfinance — skip")
                continue
            tasks.append(self._collect_one(task))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        total = sum(r for r in results if isinstance(r, int))
        failed = sum(1 for r in results if not isinstance(r, int))
        logger.info(f"Collection done: {len(tasks)} targets, {total} rows saved, {failed} failed")

        # 기업행동(배당/분할) 수집 — 수정주가 계산의 원천. 심볼 단위(타임프레임 무관)
        symbols = sorted({t.symbol for t in plan})
        action_results = await asyncio.gather(
            *[self._collect_actions_one(s) for s in symbols], return_exceptions=True
        )
        new_actions = sum(r for r in action_results if isinstance(r, int))
        action_failed = sum(1 for r in action_results if not isinstance(r, int))
        logger.info(
            f"Corporate actions done: {len(symbols)} symbols, {new_actions} new events, {action_failed} failed"
        )

    async def _collect_one(self, task: CollectionTask) -> int | None:
        """티커 1개 수집 — 개별 실패는 로그 후 None 반환 (다음 실행에서 max(time) 기준 자동 복구)"""
        try:
            async with self._fetch_sem:
                df = await asyncio.to_thread(self._fetch_history, task)

            if df.empty:
                logger.warning(f"{task.symbol} {task.timeframe}: no data received")

            # 데이터가 없어도 보관 기간 purge는 수행돼야 하므로 save는 항상 호출
            async with self._db_lock:
                saved = await self.service.save_candles(task, df)

            mode = "incremental" if task.start else "full"
            logger.info(f"{task.symbol} {task.timeframe}: {mode} collection, {saved} rows saved")
            return saved

        except Exception as e:
            logger.error(f"{task.symbol} {task.timeframe} collection failed: {e}")
            return None

    async def _collect_actions_one(self, symbol: str) -> int | None:
        """심볼 1개의 배당/분할 수집 — 개별 실패는 로그 후 None 반환"""
        try:
            async with self._fetch_sem:
                df = await asyncio.to_thread(self._fetch_actions, symbol)
            async with self._db_lock:
                return await self.action_service.save_actions(symbol, df)
        except Exception as e:
            logger.error(f"{symbol} corporate actions collection failed: {e}")
            return None

    # ── sync 영역 (asyncio.to_thread에서 실행) ─────────────────

    @staticmethod
    def _fetch_actions(symbol: str) -> pd.DataFrame:
        """yfinance actions → 표준 컬럼(time/dividends/stock splits), time은 UTC
        응답이 전체 히스토리라 증분 필터링은 service가 담당"""
        df = yf.Ticker(symbol).actions
        if df is None or df.empty:
            return pd.DataFrame()

        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"date": "time"})

        if df["time"].dt.tz is None:
            df["time"] = df["time"].dt.tz_localize("UTC")
        else:
            df["time"] = df["time"].dt.tz_convert("UTC")
        return df

    def _fetch_history(self, task: CollectionTask) -> pd.DataFrame:
        """증분: 마지막 캔들 시각부터(1개 겹쳐 재수집 — 미확정 캔들을 upsert로 보정)
        신규: 전체 히스토리(intraday는 yfinance 보존 기간 내 전체)
        티커에 retention_days가 있으면 그 범위 밖은 애초에 요청하지 않음 (가져와도 삭제 대상)"""
        interval = YF_INTERVAL_MAP[task.timeframe]
        now = datetime.now(timezone.utc)

        start = task.start
        floors = []
        yf_limit = RETENTION_LIMIT.get(task.timeframe)
        if yf_limit:
            # yfinance 보존 기간 밖 요청은 오류/빈 응답 — 하루 여유를 두고 clamp
            floors.append(now - yf_limit + timedelta(days=1))
        if task.retention_days is not None:
            floors.append(now - timedelta(days=task.retention_days))
        if floors:
            floor = max(floors)
            start = floor if start is None else max(start, floor)

        ticker = yf.Ticker(task.symbol)

        if start is None:
            # 신규 티커 (일봉 이상) — 상장 이후 전체
            df = ticker.history(period="max", interval=interval, auto_adjust=False)
            return self._normalize(df)

        chunk = REQUEST_CHUNK.get(task.timeframe)
        if chunk is None:
            df = ticker.history(start=start, interval=interval, auto_adjust=False)
            return self._normalize(df)

        # 요청당 범위 제한이 있는 timeframe(1m)은 chunk 단위로 나눠서 수집
        frames = []
        cursor = start
        while cursor < now:
            df = ticker.history(start=cursor, end=min(cursor + chunk, now),
                                interval=interval, auto_adjust=False)
            df = self._normalize(df)
            if not df.empty:
                frames.append(df)
            cursor += chunk
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    @staticmethod
    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        """yfinance 응답 → 표준 컬럼(time/open/high/low/close/volume), time은 UTC"""
        if df.empty:
            return pd.DataFrame()

        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"datetime": "time", "date": "time"})

        if df["time"].dt.tz is None:
            df["time"] = df["time"].dt.tz_localize("UTC")
        else:
            df["time"] = df["time"].dt.tz_convert("UTC")

        return df[["time", "open", "high", "low", "close", "volume"]]
