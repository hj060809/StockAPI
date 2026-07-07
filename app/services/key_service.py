from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.keys import generate_api_key, is_expired
from app.repositories.key_repo import ApiKeyRepository
from app.schemas.key_scheme import ApiKeyCreate, ApiKeyIssued

class ApiKeyService:
    def __init__(self, db: AsyncSession):
        self.repo = ApiKeyRepository(db)

    async def generate(self, data: ApiKeyCreate) -> ApiKeyIssued:
        raw_key, key_prefix, key_hash = generate_api_key()

        api_key = await self.repo.create(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=data.name,
            expires_at=data.expires_at,
        )

        return ApiKeyIssued(
            id=api_key.id,
            name=api_key.name,
            key=raw_key,
            key_prefix=key_prefix,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
        )

    async def authenticate(self, raw_key: str) -> int:
        api_key = await self.repo.get_by_raw_key(raw_key)

        if api_key is None or not api_key.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        if is_expired(api_key.expires_at):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The Key is Expired",
            )

        await self.repo.update_last_used(api_key.id)
        return api_key.id

    async def getCount(self) -> int:
        return await self.repo.count_keys()