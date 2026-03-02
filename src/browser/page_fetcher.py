import hashlib

import structlog
from playwright.async_api import BrowserContext, TimeoutError as PlaywrightTimeout

from .html_cleaner import HtmlCleaner
from .rate_limiter import RateLimiter
from .robots_checker import RobotsChecker

logger = structlog.get_logger()


class FetchResult:
    """Result of fetching a page."""

    def __init__(
        self,
        url: str,
        raw_html: str,
        cleaned_html: str,
        content_hash: str,
        status_code: int,
        title: str = "",
    ) -> None:
        self.url = url
        self.raw_html = raw_html
        self.cleaned_html = cleaned_html
        self.content_hash = content_hash
        self.status_code = status_code
        self.title = title


class PageFetcher:
    """Fetch web pages with JS rendering via Playwright."""

    def __init__(
        self,
        rate_limiter: RateLimiter,
        robots_checker: RobotsChecker,
        html_cleaner: HtmlCleaner,
        timeout_ms: int = 30_000,
    ) -> None:
        self._rate_limiter = rate_limiter
        self._robots_checker = robots_checker
        self._html_cleaner = html_cleaner
        self._timeout_ms = timeout_ms

    async def fetch(self, url: str, context: BrowserContext) -> FetchResult:
        """Fetch a page, render JS, clean HTML, and return the result."""
        # Check robots.txt compliance
        if not await self._robots_checker.is_allowed(url):
            logger.warning("robots_blocked", url=url)
            raise PermissionError(f"Blocked by robots.txt: {url}")

        # Rate limit
        await self._rate_limiter.wait(url)

        page = await context.new_page()
        try:
            # Use "load" instead of "networkidle" - many catalog sites have persistent
            # connections (analytics, chat) that prevent networkidle from firing
            response = await page.goto(url, wait_until="load", timeout=self._timeout_ms)
            status_code = response.status if response else 0

            # Wait for dynamic content to settle
            await page.wait_for_load_state("domcontentloaded")

            raw_html = await page.content()
            if not raw_html:
                raise ValueError("Page returned empty content")
            title = await page.title()

            cleaned_html = self._html_cleaner.clean(raw_html)
            content_hash = hashlib.sha256(cleaned_html.encode()).hexdigest()

            logger.info(
                "page_fetched",
                url=url,
                status=status_code,
                raw_len=len(raw_html),
                cleaned_len=len(cleaned_html),
            )

            return FetchResult(
                url=url,
                raw_html=raw_html,
                cleaned_html=cleaned_html,
                content_hash=content_hash,
                status_code=status_code,
                title=title,
            )

        except PlaywrightTimeout:
            logger.error("page_timeout", url=url, timeout_ms=self._timeout_ms)
            raise TimeoutError(f"Page load timed out: {url}")

        finally:
            await page.close()
