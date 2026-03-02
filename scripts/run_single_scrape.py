"""CLI script to run a single university scrape.

Usage:
    # Search mode (recommended) — just name + major:
    uv run python scripts/run_single_scrape.py --name "MIT" --major "Computer Science"

    # Direct URL mode:
    uv run python scripts/run_single_scrape.py --url https://catalog.csus.edu --name "Sacramento State"
"""

import argparse
import asyncio
import sys
from uuid import uuid4

from openai import AsyncOpenAI

from src.agent.orchestrator import Orchestrator
from src.browser.manager import BrowserManager
from src.config.logging_config import setup_logging
from src.config.settings import get_settings
from src.db.connection import close_pool, create_pool, run_migrations
from src.search import SearchResolver, SerpClient


async def main(url: str | None, name: str, major: str | None) -> None:
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)

    # Initialize database
    pool = await create_pool(settings.DATABASE_URL)
    await run_migrations(settings.DATABASE_URL)

    # Initialize OpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # Resolve URL via search if not provided
    seed_url = url
    if not seed_url:
        if not settings.SERP_API_KEY:
            print("ERROR: SERP_API_KEY is required for search mode. Set it in .env")
            sys.exit(1)

        print(f"\nSearching for: {name}" + (f" — {major}" if major else ""))
        serp = SerpClient(api_key=settings.SERP_API_KEY)
        resolver = SearchResolver(serp, client, model=settings.OPENAI_MODEL)
        target = await resolver.resolve(name, major)

        seed_url = target.program_url or target.catalog_url
        print(f"Resolved URL: {seed_url} (confidence: {target.confidence:.0%})")
        print(f"Normalized name: {target.university_name_normalized}\n")

    # Initialize browser
    browser = BrowserManager(pool_size=1)
    await browser.start()

    try:
        orchestrator = Orchestrator(
            openai_client=client,
            db_pool=pool,
            browser_manager=browser,
            model=settings.OPENAI_MODEL,
            token_budget=settings.TOKEN_BUDGET,
            max_content_tokens=settings.get_max_content_tokens(),
            rate_limit_delay=settings.RATE_LIMIT_DELAY,
            cache_ttl_hours=settings.CACHE_TTL_HOURS,
            page_timeout_ms=settings.PAGE_TIMEOUT_MS,
        )

        job_id = str(uuid4())
        print(f"Starting scrape job: {job_id}")
        print(f"University: {name}")
        print(f"URL: {seed_url}")
        if major:
            print(f"Major: {major}")
        print()

        if major:
            await orchestrator.run_targeted(
                job_id=job_id,
                seed_url=seed_url,
                university_name=name,
                major_name=major,
            )
        else:
            await orchestrator.run(
                job_id=job_id,
                seed_url=seed_url,
                university_name=name,
            )

        print(f"\nScrape complete! Job ID: {job_id}")

    finally:
        await browser.stop()
        await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape a university catalog")
    parser.add_argument("--url", required=False, help="University catalog URL (optional if using search)")
    parser.add_argument("--name", required=True, help="University name")
    parser.add_argument("--major", required=False, help="Major name for targeted scrape")
    args = parser.parse_args()

    if not args.url and not args.major:
        parser.error("Provide either --url for direct scraping or --major for search-based scraping")

    asyncio.run(main(args.url, args.name, args.major))
