import json

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel

from src.agent.prompts.search import URL_RESOLUTION_PROMPT
from src.agent.prompts.system import AGENT_IDENTITY, JSON_INSTRUCTIONS

from .serp_client import SerpClient

logger = structlog.get_logger()


class ResolvedTarget(BaseModel):
    """Result of resolving a university name + major into URLs."""

    catalog_url: str
    program_url: str | None = None
    university_name_normalized: str
    confidence: float = 0.0
    search_query: str = ""


class SearchResolver:
    """Resolves university name + major name into catalog URLs using SerpAPI + GPT-4o."""

    def __init__(
        self, serp_client: SerpClient, openai_client: AsyncOpenAI, model: str = "gpt-4o"
    ) -> None:
        self._serp = serp_client
        self._openai = openai_client
        self._model = model

    async def resolve(
        self, university_name: str, major_name: str | None = None
    ) -> ResolvedTarget:
        """Find the catalog URL for a university and optionally a specific major's page.

        Args:
            university_name: e.g., "MIT", "Sacramento State", "UC Berkeley"
            major_name: e.g., "Computer Science", "Mechanical Engineering"

        Returns:
            ResolvedTarget with catalog_url and optionally program_url
        """
        # Build search queries
        queries = self._build_queries(university_name, major_name)

        # Search and collect results
        all_results = []
        for query in queries:
            results = await self._serp.search(query, num_results=10)
            all_results.extend(results)

        if not all_results:
            raise ValueError(
                f"No search results found for university '{university_name}'. "
                "Please check the university name and try again."
            )

        # Deduplicate results by URL
        seen_urls: set[str] = set()
        unique_results = []
        for r in all_results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        # Use GPT-4o to pick the best URL from search results
        results_text = "\n".join(
            f"[{i+1}] {r.title}\n    URL: {r.url}\n    {r.snippet}"
            for i, r in enumerate(unique_results[:15])
        )

        prompt = URL_RESOLUTION_PROMPT.format(
            university_name=university_name,
            major_name=major_name or "N/A",
            search_results=results_text,
        )

        response = await self._openai.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": f"{AGENT_IDENTITY}\n\n{JSON_INSTRUCTIONS}"},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1024,
        )

        content = response.choices[0].message.content or "{}"
        data = json.loads(content)

        target = ResolvedTarget(
            catalog_url=data.get("catalog_url", ""),
            program_url=data.get("program_url"),
            university_name_normalized=data.get("university_name_normalized", university_name),
            confidence=data.get("confidence", 0.0),
            search_query=queries[0],
        )

        if not target.catalog_url:
            raise ValueError(
                f"Could not find a catalog URL for '{university_name}'. "
                "Try providing the catalog URL directly."
            )

        logger.info(
            "search_resolved",
            university=university_name,
            major=major_name,
            catalog_url=target.catalog_url,
            program_url=target.program_url,
            confidence=target.confidence,
        )

        return target

    @staticmethod
    def _build_queries(university_name: str, major_name: str | None) -> list[str]:
        """Build search queries for SerpAPI."""
        queries = []

        if major_name:
            # Most specific first: look for the program page directly
            queries.append(f"{university_name} {major_name} degree requirements catalog")
            queries.append(f"{university_name} {major_name} major curriculum")
        else:
            queries.append(f"{university_name} academic catalog programs")

        # Always include a general catalog search
        queries.append(f"{university_name} course catalog")

        return queries
