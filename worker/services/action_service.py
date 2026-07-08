from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger
from worker.repositories.action_repo import CorporateActionRepository
from worker.schemas.action_scheme import CorporateActionData

class ActionService:
    """기업행동(배당/분할) 이벤트 저장 — 데이터 적재만 담당.

    분할 발생 시 기존 캔들의 스케일 재동기화는 캔들 수집 경로의
    스케일 카나리아(candle_service.reconcile_scale)가 담당한다 —
    저장된 캔들과 fetch 값의 실제 불일치를 근거로 판단하므로,
    이벤트 저장 시점에 재동기화 여부를 추측할 필요가 없다.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CorporateActionRepository(db)

    async def save_actions(self, symbol: str, actions: Sequence[CorporateActionData]) -> int:
        """기업행동을 증분 저장 — 마지막 저장 시각 이후의 이벤트만 insert.
        신규 심볼은 전체 히스토리 백필"""
        if not actions:
            return 0

        last = await self.repo.get_last_time(symbol)
        if last is not None:
            actions = [a for a in actions if a.time > last]
        if not actions:
            return 0

        rows = [
            {"symbol": symbol, "time": a.time, "type": a.type, "value": a.value}
            for a in actions
        ]
        try:
            await self.repo.bulk_upsert(rows)
            await self.db.commit()
        except Exception:
            # aborted 트랜잭션이 세션에 남지 않도록 즉시 정리
            await self.db.rollback()
            raise

        logger.info(f"{symbol}: {len(rows)} new corporate actions saved")
        return len(rows)
