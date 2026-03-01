from uuid import UUID

import asyncpg
import structlog

from src.models import University

logger = structlog.get_logger()


class UniversityRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert(self, university: University) -> University:
        """Insert or update a university record."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO universities (id, name, slug, domain, catalog_url, logo_url, state, country, program_count, last_scraped_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    catalog_url = EXCLUDED.catalog_url,
                    logo_url = EXCLUDED.logo_url,
                    program_count = EXCLUDED.program_count,
                    last_scraped_at = EXCLUDED.last_scraped_at
                RETURNING *
                """,
                university.id,
                university.name,
                university.slug,
                university.domain,
                university.catalog_url,
                university.logo_url,
                university.state,
                university.country,
                university.program_count,
                university.last_scraped_at,
            )
            logger.info("university_upserted", slug=university.slug)
            return University(**dict(row))

    async def get_by_id(self, university_id: UUID) -> University | None:
        """Get a university by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM universities WHERE id = $1", university_id
            )
            return University(**dict(row)) if row else None

    async def get_by_slug(self, slug: str) -> University | None:
        """Get a university by slug."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM universities WHERE slug = $1", slug
            )
            return University(**dict(row)) if row else None

    async def list(
        self, search: str | None = None, state: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[University], int]:
        """List universities with optional filtering and pagination."""
        conditions: list[str] = []
        params: list[object] = []
        idx = 1

        if search:
            conditions.append(f"name ILIKE ${idx}")
            params.append(f"%{search}%")
            idx += 1

        if state:
            conditions.append(f"state = ${idx}")
            params.append(state)
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * page_size

        async with self._pool.acquire() as conn:
            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM universities {where}", *params
            )
            rows = await conn.fetch(
                f"SELECT * FROM universities {where} ORDER BY name LIMIT ${idx} OFFSET ${idx + 1}",
                *params,
                page_size,
                offset,
            )
            return [University(**dict(r)) for r in rows], total or 0
