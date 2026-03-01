import asyncio
import time
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger()


class RateLimiter:
    """Per-domain rate limiter to be respectful to university servers."""

    def __init__(self, delay_seconds: float = 2.0) -> None:
        self._delay = delay_seconds
        self._last_request: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc

    def _get_lock(self, domain: str) -> asyncio.Lock:
        if domain not in self._locks:
            self._locks[domain] = asyncio.Lock()
        return self._locks[domain]

    async def wait(self, url: str) -> None:
        """Wait if necessary to respect rate limits for a domain."""
        domain = self._get_domain(url)
        lock = self._get_lock(domain)

        async with lock:
            last = self._last_request.get(domain, 0.0)
            elapsed = time.monotonic() - last
            wait_time = self._delay - elapsed

            if wait_time > 0:
                logger.debug("rate_limit_waiting", domain=domain, wait_seconds=round(wait_time, 2))
                await asyncio.sleep(wait_time)

            self._last_request[domain] = time.monotonic()
