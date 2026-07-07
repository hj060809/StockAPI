from fastapi import APIRouter, status

from app.services.key_service import ApiKeyService
from app.schemas.key_scheme import ApiKeyCreate, ApiKeyIssued
from app.core.deps import DbDep, ApiKeyDep

router = APIRouter()

@router.post(
    "/",
    response_model=ApiKeyIssued,
    status_code=status.HTTP_201_CREATED,
    summary='Create new api key'
)
async def create_key(body: ApiKeyCreate, db: DbDep):
    return await ApiKeyService(db).generate(body)

@router.get("/count")
async def get_count(db: DbDep, _: ApiKeyDep):
    return await ApiKeyService(db).getCount()