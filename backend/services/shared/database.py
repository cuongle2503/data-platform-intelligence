from __future__ import annotations

import asyncpg
from typing import AsyncGenerator

from services.shared.config import settings
from services.shared.logging import get_logger

logger = get_logger(__name__)

class DatabasePool:
    _pool: asyncpg.Pool | None = None

    @classmethod
    async def connect(cls) -> None:
        if cls._pool is None:
            logger.info("Initializing asyncpg connection pool")
            cls._pool = await asyncpg.create_pool(
                dsn=settings.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60.0
            )

    @classmethod
    async def disconnect(cls) -> None:
        if cls._pool is not None:
            logger.info("Closing asyncpg connection pool")
            await cls._pool.close()
            cls._pool = None

    @classmethod
    def get_pool(cls) -> asyncpg.Pool:
        if cls._pool is None:
            raise RuntimeError("Database pool is not initialized")
        return cls._pool

async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """FastAPI Dependency for database connection."""
    pool = DatabasePool.get_pool()
    async with pool.acquire() as conn:
        yield conn
