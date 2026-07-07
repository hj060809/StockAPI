from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared_lib.models.ticker_model import CollectionTicker

class TickerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active(self) -> Sequence[CollectionTicker]:
        """수집 대상(is_active=True) 티커 목록 조회"""
        result = await self.db.execute(
            select(CollectionTicker).where(CollectionTicker.is_active.is_(True))
        )
        return result.scalars().all()

    async def update_last_collected(self, symbol: str, timeframe: str) -> None:
        """수집 성공 시각 기록 — 모니터링용 (증분 판단은 candles의 max(time) 기준)"""
        await self.db.execute(
            update(CollectionTicker)
            .where(
                CollectionTicker.symbol == symbol,
                CollectionTicker.timeframe == timeframe,
            )
            .values(last_collected_at=datetime.now(timezone.utc))
        )
