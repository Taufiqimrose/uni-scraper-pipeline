from typing import Annotated

import asyncpg
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from src.config.settings import Settings, get_settings
from src.db.connection import get_pool
from src.db.repositories import (
    CourseRepository,
    ProgramRepository,
    ScrapeJobRepository,
    UniversityRepository,
)

# OpenAPI security scheme — adds "Authorize" button to Swagger UI
_api_key_header = APIKeyHeader(name="X-API-Key")


async def get_db_pool() -> asyncpg.Pool:
    """Dependency: get the database connection pool."""
    return await get_pool()


def get_university_repo(pool: Annotated[asyncpg.Pool, Depends(get_db_pool)]) -> UniversityRepository:
    return UniversityRepository(pool)


def get_program_repo(pool: Annotated[asyncpg.Pool, Depends(get_db_pool)]) -> ProgramRepository:
    return ProgramRepository(pool)


def get_course_repo(pool: Annotated[asyncpg.Pool, Depends(get_db_pool)]) -> CourseRepository:
    return CourseRepository(pool)


def get_scrape_job_repo(pool: Annotated[asyncpg.Pool, Depends(get_db_pool)]) -> ScrapeJobRepository:
    return ScrapeJobRepository(pool)


async def verify_api_key(
    api_key: Annotated[str, Security(_api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """Verify the API key from the X-API-Key header."""
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key
