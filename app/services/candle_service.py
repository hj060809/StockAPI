from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger
from app.repositories.candle_repo import CandleRepository

class CandleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CandleRepository(db)

    async def purge_all(self) -> int:
        """모든 캔들 삭제 (수집 티커는 보존) — 삭제 행 수 반환.

        재수집은 하지 않는다. 수집은 max(time) 기반 증분이라, candles가 비면
        다음 워커 실행이 이를 신규로 보고 전체 백필을 자동 수행한다.
        (빈 상태 = 겹침 캔들 없음이라 스케일 카나리아도 깨끗한 full 경로를 탄다)"""
        deleted = await self.repo.delete_all()
        await self.db.commit()
        logger.info(f"Purged all candles: {deleted} rows deleted")
        return deleted
