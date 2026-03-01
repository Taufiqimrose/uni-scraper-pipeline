import json

import structlog
from openai import AsyncOpenAI

from src.models import ProgramDetail
from src.utils.token_counter import count_tokens, truncate_to_tokens

from .prompts.extraction import EXTRACTION_PROMPT, EXTRACTION_RETRY_PROMPT
from .prompts.system import AGENT_IDENTITY, JSON_INSTRUCTIONS

logger = structlog.get_logger()

# Reserve tokens for system prompt + response
MAX_CONTENT_TOKENS = 100_000


class ExtractorAgent:
    """Extracts structured program data from HTML pages."""

    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o") -> None:
        self._client = client
        self._model = model

    async def extract_program(
        self, page_content: str, university_name: str, program_url: str
    ) -> tuple[ProgramDetail, int]:
        """Extract structured program data from a program detail page.

        Returns:
            Tuple of (ProgramDetail, tokens_used)
        """
        # Truncate content if too large for the context window
        content_tokens = count_tokens(page_content)
        if content_tokens > MAX_CONTENT_TOKENS:
            logger.warning(
                "content_truncated",
                url=program_url,
                original_tokens=content_tokens,
                max_tokens=MAX_CONTENT_TOKENS,
            )
            page_content = truncate_to_tokens(page_content, MAX_CONTENT_TOKENS)

        prompt = EXTRACTION_PROMPT.format(
            university_name=university_name,
            program_url=program_url,
            page_content=page_content,
        )

        total_tokens_used = 0

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
                    max_tokens=16384,
                )

                content = response.choices[0].message.content or "{}"
                total_tokens_used += response.usage.total_tokens if response.usage else 0

                data = json.loads(content)
                program = ProgramDetail(**data)

                # Basic sanity check
                total_courses = sum(len(rg.courses) for rg in program.requirements)
                logger.info(
                    "extractor_success",
                    program=program.name,
                    requirement_groups=len(program.requirements),
                    total_courses=total_courses,
                    tokens=total_tokens_used,
                )
                return program, total_tokens_used

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    "extractor_parse_error",
                    attempt=attempt + 1,
                    url=program_url,
                    error=str(e),
                )
                if attempt < 2:
                    prompt = EXTRACTION_RETRY_PROMPT.format(
                        issues=str(e), page_content=page_content
                    )
                else:
                    raise

        raise RuntimeError(f"Extraction failed after 3 attempts for {program_url}")
