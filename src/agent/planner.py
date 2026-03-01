import json

import structlog
from openai import AsyncOpenAI

from src.models import NavigationPlan
from src.utils.token_counter import count_tokens

from .prompts.planning import PLANNING_PROMPT, PLANNING_RETRY_PROMPT
from .prompts.system import AGENT_IDENTITY, JSON_INSTRUCTIONS

logger = structlog.get_logger()


class PlannerAgent:
    """Analyzes a university website and produces a navigation plan."""

    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o") -> None:
        self._client = client
        self._model = model

    async def plan(
        self, page_content: str, university_name: str, seed_url: str
    ) -> tuple[NavigationPlan, int]:
        """Analyze the seed page and produce a navigation plan.

        Returns:
            Tuple of (NavigationPlan, tokens_used)
        """
        prompt = PLANNING_PROMPT.format(
            university_name=university_name,
            seed_url=seed_url,
            page_content=page_content,
        )

        input_tokens = count_tokens(AGENT_IDENTITY + JSON_INSTRUCTIONS + prompt)
        logger.info("planner_invoked", university=university_name, input_tokens=input_tokens)

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
                    max_tokens=4096,
                )

                content = response.choices[0].message.content or "{}"
                total_tokens = response.usage.total_tokens if response.usage else 0

                data = json.loads(content)
                plan = NavigationPlan(**data)

                logger.info(
                    "planner_success",
                    site_type=plan.site_type,
                    program_urls=len(plan.program_list_urls),
                    estimated_programs=plan.estimated_program_count,
                    tokens=total_tokens,
                )
                return plan, total_tokens

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("planner_parse_error", attempt=attempt + 1, error=str(e))
                if attempt < 2:
                    prompt = PLANNING_RETRY_PROMPT.format(error=str(e))
                else:
                    raise

        raise RuntimeError("Planner failed after 3 attempts")
