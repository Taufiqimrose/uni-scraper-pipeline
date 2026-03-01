import hashlib
from datetime import datetime, timedelta

import asyncpg
import structlog

logger = structlog.get_logger()


class PageCache:
    """Database-backed page cache with TTL to avoid re-fetching."""

    def __init__(self, pool: asyncpg.Pool, ttl_hours: int = 24) -> None:
        self._pool = pool
        self._ttl = timedelta(hours=ttl_hours)

    @staticmethod
    def _url_hash(url: str) -> str:
        return hashlib.sha256(url.strip().lower().encode()).hexdigest()

    async def get(self, url: str) -> str | None:
        """Get cached HTML for a URL, or None if not cached/expired."""
        url_hash = self._url_hash(url)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT content_html FROM page_cache WHERE url_hash = $1 AND expires_at > $2",
                url_hash,
                datetime.utcnow(),
            )
            if row:
                logger.debug("cache_hit", url=url)
                return row["content_html"]
            return None

    async def set(self, url: str, html: str, content_hash: str) -> None:
        """Cache HTML for a URL."""
        url_hash = self._url_hash(url)
        expires_at = datetime.utcnow() + self._ttl
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO page_cache (url_hash, url, content_html, content_hash, fetched_at, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (url_hash) DO UPDATE SET
                    content_html = EXCLUDED.content_html,
                    content_hash = EXCLUDED.content_hash,
                    fetched_at = EXCLUDED.fetched_at,
                    expires_at = EXCLUDED.expires_at
                """,
                url_hash,
                url,
                html,
                content_hash,
                datetime.utcnow(),
                expires_at,
            )
            logger.debug("cache_set", url=url)

    async def invalidate(self, url: str) -> None:
        """Remove a URL from the cache."""
        url_hash = self._url_hash(url)
        async with self._pool.acquire() as conn:
            await conn.execute("DELETE FROM page_cache WHERE url_hash = $1", url_hash)

    async def cleanup_expired(self) -> int:
        """Remove all expired cache entries. Returns count of removed rows."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM page_cache WHERE expires_at < $1", datetime.utcnow()
            )
            # result is like "DELETE 42"
            count = int(result.split()[-1]) if result else 0
            if count:
                logger.info("cache_cleanup", removed=count)
            return count
