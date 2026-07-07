from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from shared.shared_lib.config import settings

# ── 엔진 ─────────────────────────────────────────────────
# pool_size     : 평상시 유지할 커넥션 수
# max_overflow  : pool_size 초과 시 추가로 열 수 있는 최대 커넥션 수
# pool_pre_ping : 커넥션 재사용 전 살아있는지 확인 (끊긴 커넥션 방지)
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.ENV == "development",  # 개발 환경에서만 SQL 로그 출력
    connect_args={
        "ssl": "require",
        "statement_cache_size": 0,  # ← Pooler 사용 시 필수
    },
)

# ── 세션 팩토리 ───────────────────────────────────────────
# autocommit=False : 명시적으로 commit() 해야 반영됨
# autoflush=False  : commit 전에 자동으로 flush 하지 않음
# expire_on_commit : commit 후 객체 속성을 만료시키지 않음
#                    (async에서 commit 후 lazy load 방지)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

@asynccontextmanager
async def get_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()