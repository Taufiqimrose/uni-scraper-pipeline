from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import structlog

logger = structlog.get_logger()


class RobotsChecker:
    """Check robots.txt compliance before fetching pages."""

    def __init__(self, user_agent: str = "UniScraperBot/1.0") -> None:
        self._user_agent = user_agent
        self._parsers: dict[str, RobotFileParser | None] = {}

    async def is_allowed(self, url: str) -> bool:
        """Check if a URL is allowed by the site's robots.txt."""
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if domain not in self._parsers:
            await self._load_robots(domain)

        parser = self._parsers.get(domain)
        if parser is None:
            # If we couldn't load robots.txt, allow by default
            return True

        return parser.can_fetch(self._user_agent, url)

    async def _load_robots(self, domain: str) -> None:
        """Fetch and parse robots.txt for a domain."""
        robots_url = f"{domain}/robots.txt"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(robots_url)

            if response.status_code == 200:
                parser = RobotFileParser()
                parser.parse(response.text.splitlines())
                self._parsers[domain] = parser
                logger.info("robots_loaded", domain=domain)
            else:
                # No robots.txt or error -> allow everything
                self._parsers[domain] = None
                logger.info("robots_not_found", domain=domain, status=response.status_code)

        except httpx.HTTPError:
            self._parsers[domain] = None
            logger.warning("robots_fetch_failed", domain=domain)
