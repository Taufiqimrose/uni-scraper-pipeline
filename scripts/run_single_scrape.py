"""CLI script to run a single university scrape.

Usage:
    uv run python scripts/run_single_scrape.py --url https://catalog.csus.edu --name "Sacramento State"
"""

import argparse
import asyncio
import sys
from uuid import uuid4

from src.agent.orchestrator import Orchestrator
from src.browser.manager import BrowserManager
from src.config.logging_config import setup_logging
from src.config.settings import get_settings
from src.db.connection import close_pool, create_pool, run_migrations

from openai import AsyncOpenAI


async def main(url: str, name: str) -> None:
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)

    # Initialize database
    pool = await create_pool(settings.DATABASE_URL)
    await run_migrations(settings.DATABASE_URL)

    # Initialize browser
    browser = BrowserManager(pool_size=1)
    await browser.start()

    # Initialize OpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        orchestrator = Orchestrator(
            openai_client=client,
            db_pool=pool,
            browser_manager=browser,
            model=settings.OPENAI_MODEL,
            token_budget=settings.TOKEN_BUDGET,
            rate_limit_delay=settings.RATE_LIMIT_DELAY,
            cache_ttl_hours=settings.CACHE_TTL_HOURS,
            page_timeout_ms=settings.PAGE_TIMEOUT_MS,
        )

        job_id = str(uuid4())
        print(f"\nStarting scrape job: {job_id}")
        print(f"University: {name}")
        print(f"URL: {url}\n")

        await orchestrator.run(job_id=job_id, seed_url=url, university_name=name)

        print(f"\nScrape complete! Job ID: {job_id}")

    finally:
        await browser.stop()
        await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape a university catalog")
    parser.add_argument("--url", required=True, help="University catalog URL")
    parser.add_argument("--name", required=True, help="University name")
    args = parser.parse_args()

    asyncio.run(main(args.url, args.name))
