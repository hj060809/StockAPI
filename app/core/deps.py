from typing import Annotated
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared_lib.database import get_session
from app.services.key_service import ApiKeyService

async def get_db():
    async with get_session() as session:
        yield session

DbDep = Annotated[AsyncSession, Depends(get_db)]

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def auth_key(
    raw_key: Annotated[str | None, Security(api_key_header)],
    db: DbDep,
) -> int:
    if raw_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key Header is neccessary",
        )
    return await ApiKeyService(db).authenticate(raw_key)

ApiKeyDep = Annotated[int, Depends(auth_key)]