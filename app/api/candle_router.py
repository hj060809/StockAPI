from fastapi import APIRouter

from app.services.candle_service import CandleService
from app.schemas.candle_scheme import PurgeResult
from app.core.deps import DbDep, ApiKeyDep

router = APIRouter()

@router.delete(
    "/",
    response_model=PurgeResult,
    summary="Purge all candles (tickers preserved)",
)
async def purge_candles(db: DbDep, _: ApiKeyDep):
    """모든 캔들 삭제. 재수집은 다음 워커 실행이 자동으로 전체 백필로 수행"""
    deleted = await CandleService(db).purge_all()
    return PurgeResult(deleted=deleted)
