from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from data.schemas.config import Settings

settings = Settings()

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_redis():
    if not settings.redis_url:
        return _NullRedis()
    import redis.asyncio as aioredis
    pool = aioredis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)
    return aioredis.Redis(connection_pool=pool)


class _NullRedis:
    """No-op Redis for dev mode without Redis."""
    async def get(self, key): return None
    async def set(self, key, value, ex=None): pass
    async def ping(self): return True


def get_settings() -> Settings:
    return settings
