import json

import structlog
from openai import AsyncOpenAI

from src.models import DiscoveredProgram
from src.utils.token_counter import count_tokens

from .prompts.navigation import NAVIGATION_PROMPT, PAGE_CLASSIFICATION_PROMPT
from .prompts.system import AGENT_IDENTITY, JSON_INSTRUCTIONS

logger = structlog.get_logger()


class NavigatorAgent:
    """Discovers program links from university catalog pages."""

    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o") -> None:
        self._client = client
        self._model = model

    async def discover_programs(
        self,
        page_content: str,
        university_name: str,
        page_url: str,
        programs_found: int = 0,
    ) -> tuple[list[DiscoveredProgram], list[str], int]:
        """Extract program links from a page.

        Returns:
            Tuple of (discovered_programs, pagination_urls, tokens_used)
        """
        prompt = NAVIGATION_PROMPT.format(
            university_name=university_name,
            page_url=page_url,
            programs_found=programs_found,
            page_content=page_content,
        )

        input_tokens = count_tokens(AGENT_IDENTITY + JSON_INSTRUCTIONS + prompt)
        logger.info("navigator_invoked", url=page_url, input_tokens=input_tokens)

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": f"{AGENT_IDENTITY}\n\n{JSON_INSTRUCTIONS}"},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=8192,
        )

        content = response.choices[0].message.content or "{}"
        total_tokens = response.usage.total_tokens if response.usage else 0

        data = json.loads(content)
        programs = [DiscoveredProgram(**p) for p in data.get("programs", [])]
        pagination_urls = data.get("pagination_urls", [])

        logger.info(
            "navigator_success",
            programs_found=len(programs),
            pagination_urls=len(pagination_urls),
            tokens=total_tokens,
        )
        return programs, pagination_urls, total_tokens

    async def classify_page(self, page_content: str) -> tuple[dict[str, object], int]:
        """Classify what type of page this is.

        Returns:
            Tuple of (classification_dict, tokens_used)
        """
        prompt = PAGE_CLASSIFICATION_PROMPT.format(page_content=page_content)

        response = await self._client.chat.completions.create(
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
        total_tokens = response.usage.total_tokens if response.usage else 0

        return json.loads(content), total_tokens
