import calendar
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger
from worker.repositories.action_repo import CorporateActionRepository
from worker.repositories.candle_repo import CandleRepository
from worker.repositories.ticker_repo import TickerRepository
from worker.schemas.candle_scheme import CandleData

# timeframe별 캔들 기간 — 미확정(진행 중) 캔들 판별용
_FIXED_DURATION = {
    '1m': timedelta(minutes=1), '5m': timedelta(minutes=5), '15m': timedelta(minutes=15),
    '30m': timedelta(minutes=30), '1h': timedelta(hours=1), '4h': timedelta(hours=4),
    '12h': timedelta(hours=12), '1d': timedelta(days=1), '3d': timedelta(days=3),
    '1w': timedelta(weeks=1), '2w': timedelta(weeks=2),
}
# 월 단위는 길이가 가변이라 달력 계산 필요
_MONTH_DURATION = {'1M': 1, '3M': 3, '6M': 6, '1y': 12}

# 스케일 카나리아 허용오차 — 소급 수정이 없으면 겹침 캔들의 재fetch 값은 저장값과
# 동일해 비율이 정확히 1. 여유분은 Numeric(18,6) 반올림 노이즈 대비
SCALE_TOLERANCE = Decimal("0.001")

def _period_end(start: datetime, timeframe: str) -> datetime:
    """캔들 기간의 종료 시각 — 이 시각이 지나야 확정 캔들"""
    if timeframe in _FIXED_DURATION:
        return start + _FIXED_DURATION[timeframe]
    months = _MONTH_DURATION[timeframe]
    month0 = start.month - 1 + months
    year, month = start.year + month0 // 12, month0 % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)

def _is_valid(candle: CandleData) -> bool:
    """불량 캔들(가격 0, high<low 등) 판별.
    low ≤ min(open,close) ≤ max(open,close) ≤ high 이므로 low ≤ high도 함께 보장됨"""
    return (
        candle.low > 0
        and candle.low <= min(candle.open, candle.close)
        and max(candle.open, candle.close) <= candle.high
        and candle.volume >= 0
    )

def _diagnose_revision(
    stored_close: Decimal,
    fetched_close: Decimal,
    split_ratios: Sequence[Decimal],
) -> Literal["consistent", "split", "unknown"]:
    """겹침 캔들(같은 시각)의 저장 종가와 재fetch 종가를 비교해 소급 수정을 판별.

    consistent: 수정 없음 (비율 ≈ 1)
    split:      비율이 미적용 분할들의 곱과 일치 — apply_split로 정밀 복구 가능
    unknown:    분할로 설명되지 않는 수정 (데이터 정정 등) — 전체 재수집 필요
    """
    measured = stored_close / fetched_close
    if abs(measured - 1) <= SCALE_TOLERANCE:
        return "consistent"
    expected = math.prod(split_ratios, start=Decimal(1))
    if split_ratios and abs(measured / expected - 1) <= SCALE_TOLERANCE:
        return "split"
    return "unknown"

@dataclass
class CollectionTask:
    """수집 단위 — start가 None이면 신규 티커(전체 히스토리 수집)
    retention_days가 None이면 무제한 보관. last_close는 스케일 카나리아 기준값"""
    symbol: str
    timeframe: str
    start: datetime | None
    retention_days: int | None
    last_close: Decimal | None = None

class CandleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.candle_repo = CandleRepository(db)
        self.ticker_repo = TickerRepository(db)
        self.action_repo = CorporateActionRepository(db)

    async def get_collection_plan(self) -> list[CollectionTask]:
        """active 티커 목록 + 마지막 캔들(시각/종가)을 매칭해 수집 계획 산출"""
        tickers = await self.ticker_repo.get_active()
        last_candles = await self.candle_repo.get_last_candles()
        plan = []
        for t in tickers:
            retention = t.retention_days
            if retention is not None and retention <= 0:
                # 음수면 cutoff가 미래가 되어 전체 데이터가 삭제됨 — 무제한으로 처리
                logger.warning(
                    f"{t.symbol} {t.timeframe}: invalid retention_days={retention} — treated as unlimited"
                )
                retention = None
            last_time, last_close = last_candles.get((t.symbol, t.timeframe), (None, None))
            plan.append(
                CollectionTask(
                    symbol=t.symbol,
                    timeframe=t.timeframe,
                    start=last_time,
                    retention_days=retention,
                    last_close=last_close,
                )
            )
        return plan

    async def reconcile_scale(self, task: CollectionTask, candles: Sequence[CandleData]) -> bool:
        """스케일 카나리아 — 겹침 캔들(fetch 결과 중 time == task.start)의 종가를
        저장값과 비교해 소급 수정을 감지하고, 저장 전에 기존 행을 정합 상태로 복구한다.

        - 분할로 설명되는 수정: 미적용 분할(ex-date > task.start — 이후의 분할은 저장 행에
          반영됐을 수 없음이 보장됨)을 정확한 비율로 apply_split. 이 자리에서 commit —
          이후 save_candles가 실패해도 '치유된 스케일 + 새 행 없음'으로 남아 정합 유지.
        - 설명 불가한 수정: True 반환 — 호출자가 전체 재수집으로 전환해야 함.
        - 겹침 캔들이 없으면(신규 티커, clamp로 범위 밖 등) 판단 보류.
        """
        if task.start is None or task.last_close is None:
            return False
        overlap = next((c for c in candles if c.time == task.start), None)
        if overlap is None or overlap.close <= 0:
            return False

        splits = await self.action_repo.get_splits_after(task.symbol, task.start)
        verdict = _diagnose_revision(task.last_close, overlap.close, [v for _, v in splits])
        if verdict == "consistent":
            return False

        if verdict == "split":
            try:
                for ex_time, ratio in splits:
                    updated = await self.candle_repo.apply_split(
                        task.symbol, task.timeframe, ex_time, ratio
                    )
                    logger.info(
                        f"{task.symbol} {task.timeframe}: split {ratio}:1 (ex-date {ex_time.date()})"
                        f" — rescaled {updated} candles"
                    )
                await self.db.commit()
            except Exception:
                # aborted 트랜잭션이 세션에 남지 않도록 즉시 정리
                await self.db.rollback()
                raise
            return False

        logger.error(
            f"{task.symbol} {task.timeframe}: history revised beyond known splits "
            f"(stored close {task.last_close} vs fetched {overlap.close} at {task.start}) — full refetch"
        )
        return True

    async def save_candles(self, task: CollectionTask, candles: Sequence[CandleData]) -> int:
        """보관 기간 밖 캔들 삭제 + 캔들 upsert를 한 트랜잭션으로 처리.
        (symbol, timeframe) 단위로 commit — 한 티커 실패가 다른 티커를 롤백하지 않게 함"""
        rows = self._to_rows(task.symbol, task.timeframe, candles)

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
    def _to_rows(symbol: str, timeframe: str, candles: Sequence[CandleData]) -> list[dict]:
        """caller가 넘긴 CandleData 목록에 저장 정책을 적용해 DB 행 dict로 변환"""
        # 같은 시각 캔들이 겹치면(미확정+확정, chunk 경계 등) 한 INSERT 안에서
        # ON CONFLICT가 같은 행을 두 번 만나 CardinalityViolation — 최신 것만 유지
        deduped = {c.time: c for c in candles}.values()

        # 진행 중(미확정) 캔들은 저장하지 않음 — 백테스트 lookahead 방지.
        # 확정되면 다음 실행에서 자동 수집됨 (증분 시작점 = 저장된 max(time))
        now = datetime.now(timezone.utc)
        confirmed = [c for c in deduped if _period_end(c.time, timeframe) <= now]

        # 품질 검증 — 소스가 간혹 반환하는 불량 캔들 차단
        valid = [c for c in confirmed if _is_valid(c)]
        if len(valid) < len(confirmed):
            logger.warning(
                f"{symbol} {timeframe}: dropped {len(confirmed) - len(valid)} invalid rows (bad OHLCV)"
            )

        return [
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "time": c.time,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in valid
        ]
