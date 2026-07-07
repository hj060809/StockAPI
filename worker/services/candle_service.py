import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger
from worker.repositories.candle_repo import CandleRepository
from worker.repositories.ticker_repo import TickerRepository

# timeframe별 캔들 기간 — 미확정(진행 중) 캔들 판별용
_FIXED_DURATION = {
    '1m': timedelta(minutes=1), '5m': timedelta(minutes=5), '15m': timedelta(minutes=15),
    '30m': timedelta(minutes=30), '1h': timedelta(hours=1), '4h': timedelta(hours=4),
    '12h': timedelta(hours=12), '1d': timedelta(days=1), '3d': timedelta(days=3),
    '1w': timedelta(weeks=1), '2w': timedelta(weeks=2),
}
# 월 단위는 길이가 가변이라 달력 계산 필요
_MONTH_DURATION = {'1M': 1, '3M': 3, '6M': 6, '1y': 12}

def _period_end(start: datetime, timeframe: str) -> datetime:
    """캔들 기간의 종료 시각 — 이 시각이 지나야 확정 캔들"""
    if timeframe in _FIXED_DURATION:
        return start + _FIXED_DURATION[timeframe]
    months = _MONTH_DURATION[timeframe]
    month0 = start.month - 1 + months
    year, month = start.year + month0 // 12, month0 % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)

@dataclass
class CollectionTask:
    """수집 단위 — start가 None이면 신규 티커(전체 히스토리 수집)
    retention_days가 None이면 무제한 보관"""
    symbol: str
    timeframe: str
    start: datetime | None
    retention_days: int | None

class CandleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.candle_repo = CandleRepository(db)
        self.ticker_repo = TickerRepository(db)

    async def get_collection_plan(self) -> list[CollectionTask]:
        """active 티커 목록 + 마지막 캔들 시각을 매칭해 수집 계획 산출"""
        tickers = await self.ticker_repo.get_active()
        last_times = await self.candle_repo.get_last_times()
        plan = []
        for t in tickers:
            retention = t.retention_days
            if retention is not None and retention <= 0:
                # 음수면 cutoff가 미래가 되어 전체 데이터가 삭제됨 — 무제한으로 처리
                logger.warning(
                    f"{t.symbol} {t.timeframe}: invalid retention_days={retention} — treated as unlimited"
                )
                retention = None
            plan.append(
                CollectionTask(
                    symbol=t.symbol,
                    timeframe=t.timeframe,
                    start=last_times.get((t.symbol, t.timeframe)),
                    retention_days=retention,
                )
            )
        return plan

    async def save_candles(self, task: CollectionTask, df: pd.DataFrame) -> int:
        """보관 기간 밖 캔들 삭제 + DataFrame upsert를 한 트랜잭션으로 처리.
        (symbol, timeframe) 단위로 commit — 한 티커 실패가 다른 티커를 롤백하지 않게 함"""
        rows = self._to_rows(task.symbol, task.timeframe, df) if not df.empty else []

        purged = 0
        try:
            if task.retention_days is not None and task.retention_days > 0:
                cutoff = datetime.now(timezone.utc) - timedelta(days=task.retention_days)
                purged = await self.candle_repo.delete_before(task.symbol, task.timeframe, cutoff)

            if rows:
                await self.candle_repo.bulk_upsert(rows)
            await self.ticker_repo.update_last_collected(task.symbol, task.timeframe)
            await self.db.commit()
        except Exception:
            # aborted 트랜잭션이 세션에 남으면 이후 티커 저장까지 전부 실패함
            await self.db.rollback()
            raise

        if purged:
            logger.info(f"{task.symbol} {task.timeframe}: purged {purged} rows past retention ({task.retention_days}d)")
        return len(rows)

    @staticmethod
    def _to_rows(symbol: str, timeframe: str, df: pd.DataFrame) -> list[dict]:
        """caller가 넘긴 표준 DataFrame(time/open/high/low/close/volume) → DB 행 dict"""
        df = df.dropna(subset=["open", "high", "low", "close"])
        # 같은 시각 캔들이 겹치면(미확정+확정, chunk 경계 등) 한 INSERT 안에서
        # ON CONFLICT가 같은 행을 두 번 만나 CardinalityViolation — 최신 것만 유지
        df = df.drop_duplicates(subset=["time"], keep="last")
        # 진행 중(미확정) 캔들은 저장하지 않음 — 백테스트 lookahead 방지.
        # 확정되면 다음 실행에서 자동 수집됨 (증분 시작점 = 저장된 max(time))
        now = datetime.now(timezone.utc)
        df = df[[_period_end(t, timeframe) <= now for t in df["time"]]]
        return [
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "time": t.to_pydatetime(),
                "open": Decimal(str(o)),
                "high": Decimal(str(h)),
                "low": Decimal(str(l)),
                "close": Decimal(str(c)),
                "volume": 0 if pd.isna(v) else int(v),
            }
            for t, o, h, l, c, v in zip(
                df["time"], df["open"], df["high"], df["low"], df["close"], df["volume"]
            )
        ]
