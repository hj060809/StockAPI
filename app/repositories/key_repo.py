from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from shared.shared_lib.models.key_model import ApiKey
from app.core.keys import _hash_key

class ApiKeyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_raw_key(self, raw_key: str) -> ApiKey | None:
        """평문 키를 해시한 뒤 DB에서 조회합니다."""
        key_hash = _hash_key(raw_key)
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def create(self, key_hash: str, key_prefix: str, name: str, expires_at: datetime | None) -> ApiKey:
        api_key = ApiKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            expires_at=expires_at,
        )
        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)
        return api_key
    
    async def update_last_used(self, api_key_id: int) -> None:
        """인증 성공 시 마지막 사용 시각을 갱신합니다."""
        await self.db.execute(
            update(ApiKey)
            .where(ApiKey.id == api_key_id)
            .values(last_used_at=datetime.utcnow())
        )
        await self.db.commit()

    async def count_keys(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ApiKey)
        )

        return result.scalar_one()