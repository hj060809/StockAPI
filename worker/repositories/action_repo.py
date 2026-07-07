from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared_lib.models.action_model import CorporateAction

UPSERT_CHUNK_SIZE = 1_000

class CorporateActionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_last_time(self, symbol: str) -> datetime | None:
        """심볼의 마지막 기업행동 시각 — 증분 저장의 기준점"""
        result = await self.db.execute(
            select(func.max(CorporateAction.time))
            .where(CorporateAction.symbol == symbol)
        )
        return result.scalar_one_or_none()

    async def bulk_upsert(self, rows: list[dict]) -> None:
        """기업행동 bulk upsert. commit은 호출자 책임"""
        for i in range(0, len(rows), UPSERT_CHUNK_SIZE):
            chunk = rows[i:i + UPSERT_CHUNK_SIZE]
            stmt = insert(CorporateAction).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol", "time", "type"],
                set_={"value": stmt.excluded.value},
            )
            await self.db.execute(stmt)
