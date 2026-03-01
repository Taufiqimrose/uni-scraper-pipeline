from pathlib import Path
from typing import AsyncGenerator

import asyncpg
import structlog

logger = structlog.get_logger()

_pool: asyncpg.Pool | None = None


async def create_pool(database_url: str, min_size: int = 2, max_size: int = 10) -> asyncpg.Pool:
    """Create and return a connection pool."""
    global _pool
    if _pool is not None:
        return _pool

    _pool = await asyncpg.create_pool(
        database_url,
        min_size=min_size,
        max_size=max_size,
    )
    logger.info("database_pool_created", min_size=min_size, max_size=max_size)
    return _pool


async def get_pool() -> asyncpg.Pool:
    """Get the existing connection pool."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call create_pool() first.")
    return _pool


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("database_pool_closed")


async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get a database connection from the pool."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def run_migrations(database_url: str) -> None:
    """Run all SQL migration files in order."""
    migrations_dir = Path(__file__).parent / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    conn = await asyncpg.connect(database_url)
    try:
        for migration_file in migration_files:
            sql = migration_file.read_text()
            await conn.execute(sql)
            logger.info("migration_applied", file=migration_file.name)
    finally:
        await conn.close()
