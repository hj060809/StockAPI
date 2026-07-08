from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared_lib.models.action_model import CorporateAction

UPSERT_CHUNK_SIZE = 1_000

class CorporateActionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_splits_after(self, symbol: str, after: datetime) -> list[tuple[datetime, Decimal]]:
        """after 이후 ex-date의 분할 이벤트 (time 오름차순) —
        스케일 카나리아가 감지한 소급 수정을 설명하는 근거"""
        result = await self.db.execute(
            select(CorporateAction.time, CorporateAction.value)
            .where(
                CorporateAction.symbol == symbol,
                CorporateAction.type == "split",
                CorporateAction.time > after,
            )
            .order_by(CorporateAction.time)
        )
        return [(row[0], row[1]) for row in result.all()]

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
