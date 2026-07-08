from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared_lib.models.candle_model import Candle

class CandleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def delete_all(self) -> int:
        """모든 캔들 삭제 — 삭제 행 수 반환. commit은 호출자 책임"""
        result = await self.db.execute(delete(Candle))
        return result.rowcount
