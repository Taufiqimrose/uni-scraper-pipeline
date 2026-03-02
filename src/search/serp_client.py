import httpx
import structlog
from pydantic import BaseModel

logger = structlog.get_logger()

SERP_API_URL = "https://serpapi.com/search"


class SerpResult(BaseModel):
    """A single search result from SerpAPI."""

    title: str
    url: str
    snippet: str
    position: int


class SerpClient:
    """Thin wrapper around SerpAPI for Google search."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, query: str, num_results: int = 10) -> list[SerpResult]:
        """Search Google via SerpAPI and return structured results."""
        params = {
            "q": query,
            "api_key": self._api_key,
            "engine": "google",
            "num": num_results,
            "gl": "us",
            "hl": "en",
        }

        logger.info("serp_search", query=query, num_results=num_results)

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(SERP_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

        organic = data.get("organic_results", [])
        results = []
        for item in organic[:num_results]:
            results.append(
                SerpResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    position=item.get("position", 0),
                )
            )

        logger.info("serp_results", count=len(results), query=query)
        return results
