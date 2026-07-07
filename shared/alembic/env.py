import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

from shared.shared_lib.config import settings
from shared.shared_lib.models.base import Base
import shared.shared_lib.models  # ← 모든 모델 import 필수

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata  # ← ORM 모델 전체를 바라봄


def run_migrations_offline():
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = create_async_engine(
        settings.DATABASE_URL,
        connect_args={
            "ssl": "require",
            "statement_cache_size": 0,  # ← 추가
        }
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())