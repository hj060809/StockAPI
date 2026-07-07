from datetime import datetime

from sqlalchemy import select, func, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared_lib.models.candle_model import Candle

# asyncpg 파라미터 한도(32,767) 및 Supabase pooler(statement_cache_size=0)를 고려한 배치 크기
# 8컬럼 × 1,000행 = 8,000 파라미터로 여유 있음
UPSERT_CHUNK_SIZE = 1_000

class CandleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_last_times(self) -> dict[tuple[str, str], datetime]:
        """(symbol, timeframe)별 마지막 캔들 시각 — 증분 수집의 시작점 (단일 진실 소스)"""
        result = await self.db.execute(
            select(Candle.symbol, Candle.timeframe, func.max(Candle.time))
            .group_by(Candle.symbol, Candle.timeframe)
        )
        return {(row[0], row[1]): row[2] for row in result.all()}

    async def delete_before(self, symbol: str, timeframe: str, cutoff: datetime) -> int:
        """보관 기간을 벗어난 과거 캔들 삭제. commit은 호출자 책임 — 삭제 행 수 반환"""
        result = await self.db.execute(
            delete(Candle).where(
                Candle.symbol == symbol,
                Candle.timeframe == timeframe,
                Candle.time < cutoff,
            )
        )
        return result.rowcount

    async def bulk_upsert(self, rows: list[dict]) -> None:
        """캔들 bulk upsert — PK 충돌 시 OHLCV 갱신 (미확정이던 캔들 보정용). commit은 호출자 책임"""
        for i in range(0, len(rows), UPSERT_CHUNK_SIZE):
            chunk = rows[i:i + UPSERT_CHUNK_SIZE]
            stmt = insert(Candle).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol", "timeframe", "time"],
                set_={c: stmt.excluded[c] for c in ("open", "high", "low", "close", "volume")},
            )
            await self.db.execute(stmt)
