import json

import structlog
from openai import AsyncOpenAI

from src.utils.token_counter import count_tokens

from .prompts.search import FIND_PROGRAM_PROMPT
from .prompts.system import AGENT_IDENTITY, JSON_INSTRUCTIONS

logger = structlog.get_logger()


class FinderAgent:
    """Locates a specific major/program page on a university catalog site."""

    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o") -> None:
        self._client = client
        self._model = model

    async def find_program(
        self,
        page_content: str,
        university_name: str,
        major_name: str,
        page_url: str,
    ) -> tuple[str | None, list[str], int]:
        """Find the URL to a specific program's page from a catalog page.

        Args:
            page_content: Cleaned HTML of the catalog page
            university_name: Name of the university
            major_name: Name of the major to find
            page_url: URL of the current page (for resolving relative links)

        Returns:
            Tuple of (program_url, alternative_urls, tokens_used)
            program_url is None if the program wasn't found on this page
        """
        prompt = FIND_PROGRAM_PROMPT.format(
            university_name=university_name,
            major_name=major_name,
            page_url=page_url,
            page_content=page_content,
        )

        input_tokens = count_tokens(AGENT_IDENTITY + JSON_INSTRUCTIONS + prompt)
        logger.info(
            "finder_invoked",
            major=major_name,
            page_url=page_url,
            input_tokens=input_tokens,
        )

        for attempt in range(3):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": f"{AGENT_IDENTITY}\n\n{JSON_INSTRUCTIONS}"},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=2048,
                )

                content = response.choices[0].message.content or "{}"
                total_tokens = response.usage.total_tokens if response.usage else 0

                data = json.loads(content)
                program_url = data.get("program_url")
                alternatives = data.get("alternative_urls", [])
                confidence = data.get("confidence", 0.0)

                logger.info(
                    "finder_result",
                    major=major_name,
                    found=program_url is not None,
                    confidence=confidence,
                    alternatives=len(alternatives),
                    tokens=total_tokens,
                )

                return program_url, alternatives, total_tokens

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("finder_parse_error", attempt=attempt + 1, error=str(e))
                if attempt == 2:
                    raise

        return None, [], 0
