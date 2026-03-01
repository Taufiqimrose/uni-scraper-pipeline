import asyncio

import structlog
from playwright.async_api import Browser, Playwright, async_playwright

logger = structlog.get_logger()


class BrowserManager:
    """Manages a pool of Playwright browser contexts."""

    def __init__(self, pool_size: int = 3) -> None:
        self._pool_size = pool_size
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._semaphore = asyncio.Semaphore(pool_size)

    async def start(self) -> None:
        """Launch the browser."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )
        logger.info("browser_started", pool_size=self._pool_size)

    async def stop(self) -> None:
        """Close the browser and Playwright."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("browser_stopped")

    async def new_context(self) -> "BrowserContextWrapper":
        """Acquire a browser context from the pool."""
        await self._semaphore.acquire()
        if not self._browser:
            raise RuntimeError("Browser not started. Call start() first.")
        context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
        )
        return BrowserContextWrapper(context, self._semaphore)


class BrowserContextWrapper:
    """Wraps a browser context with automatic cleanup and semaphore release."""

    def __init__(self, context: object, semaphore: asyncio.Semaphore) -> None:
        self._context = context
        self._semaphore = semaphore

    async def __aenter__(self) -> object:
        return self._context

    async def __aexit__(self, *args: object) -> None:
        await self._context.close()  # type: ignore[union-attr]
        self._semaphore.release()
