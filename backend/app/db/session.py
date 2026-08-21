from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from backend.app.core.config import settings


engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}

if settings.app_env.lower() == "testing":
    engine_kwargs["poolclass"] = NullPool


engine = create_async_engine(
    settings.database_url,
    **engine_kwargs,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def close_db() -> None:
    await engine.dispose()