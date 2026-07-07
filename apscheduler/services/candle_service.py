from sqlalchemy.ext.asyncio import AsyncSession

from apscheduler.repositories.candle_repo import CandleRepository

class CandleService:
    def __init__(self, db: AsyncSession):
        self.repo = CandleRepository(db)