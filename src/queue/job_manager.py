import structlog
from openai import AsyncOpenAI

from src.agent.orchestrator import Orchestrator
from src.browser.manager import BrowserManager
from src.config.settings import get_settings
from src.db.connection import get_pool
from src.models import ScrapeRequest

logger = structlog.get_logger()


class JobManager:
    """Manages scrape job execution."""

    async def process_job(self, job_id: str, request: ScrapeRequest) -> None:
        """Process a single scrape job."""
        settings = get_settings()
        pool = await get_pool()

        openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        browser = BrowserManager(pool_size=settings.BROWSER_POOL_SIZE)
        await browser.start()

        try:
            orchestrator = Orchestrator(
                openai_client=openai_client,
                db_pool=pool,
                browser_manager=browser,
                model=settings.OPENAI_MODEL,
                token_budget=settings.TOKEN_BUDGET,
                rate_limit_delay=settings.RATE_LIMIT_DELAY,
                cache_ttl_hours=settings.CACHE_TTL_HOURS,
                page_timeout_ms=settings.PAGE_TIMEOUT_MS,
            )

            await orchestrator.run(
                job_id=job_id,
                seed_url=request.url,
                university_name=request.university_name,
            )

        except Exception as e:
            logger.error("job_failed", job_id=job_id, error=str(e))
            raise

        finally:
            await browser.stop()
