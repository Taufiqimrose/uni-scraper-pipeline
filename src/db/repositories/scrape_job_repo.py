import json
from datetime import datetime
from uuid import UUID

import asyncpg
import structlog

from src.models import ScrapeJob, ScrapeStatus

logger = structlog.get_logger()


class ScrapeJobRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(self, job: ScrapeJob) -> ScrapeJob:
        """Create a new scrape job."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO scrape_jobs (id, university_name, seed_url, status, progress, current_step)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                job.id,
                job.university_name,
                job.seed_url,
                job.status.value,
                job.progress,
                job.current_step,
            )
            logger.info("scrape_job_created", job_id=str(job.id))
            return self._row_to_job(row)

    async def get_by_id(self, job_id: UUID) -> ScrapeJob | None:
        """Get a scrape job by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM scrape_jobs WHERE id = $1", job_id)
            return self._row_to_job(row) if row else None

    async def update_status(
        self,
        job_id: UUID,
        status: ScrapeStatus,
        *,
        progress: float | None = None,
        current_step: str | None = None,
        programs_found: int | None = None,
        programs_scraped: int | None = None,
        courses_found: int | None = None,
        error_message: str | None = None,
        total_tokens_used: int | None = None,
        total_pages_fetched: int | None = None,
    ) -> None:
        """Update a scrape job's status and metrics."""
        updates = ["status = $2"]
        params: list[object] = [job_id, status.value]
        idx = 3

        if progress is not None:
            updates.append(f"progress = ${idx}")
            params.append(progress)
            idx += 1

        if current_step is not None:
            updates.append(f"current_step = ${idx}")
            params.append(current_step)
            idx += 1

        if programs_found is not None:
            updates.append(f"programs_found = ${idx}")
            params.append(programs_found)
            idx += 1

        if programs_scraped is not None:
            updates.append(f"programs_scraped = ${idx}")
            params.append(programs_scraped)
            idx += 1

        if courses_found is not None:
            updates.append(f"courses_found = ${idx}")
            params.append(courses_found)
            idx += 1

        if error_message is not None:
            updates.append(f"error_message = ${idx}")
            params.append(error_message)
            idx += 1

        if total_tokens_used is not None:
            updates.append(f"total_tokens_used = ${idx}")
            params.append(total_tokens_used)
            idx += 1

        if total_pages_fetched is not None:
            updates.append(f"total_pages_fetched = ${idx}")
            params.append(total_pages_fetched)
            idx += 1

        if status == ScrapeStatus.RUNNING:
            updates.append(f"started_at = ${idx}")
            params.append(datetime.utcnow())
            idx += 1
        elif status in (ScrapeStatus.COMPLETED, ScrapeStatus.FAILED, ScrapeStatus.PARTIAL):
            updates.append(f"completed_at = ${idx}")
            params.append(datetime.utcnow())
            idx += 1

        set_clause = ", ".join(updates)
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"UPDATE scrape_jobs SET {set_clause} WHERE id = $1", *params
            )

    async def append_log(self, job_id: UUID, entry: dict) -> None:  # type: ignore[type-arg]
        """Append an entry to the agent log."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE scrape_jobs
                SET agent_log = agent_log || $2::jsonb
                WHERE id = $1
                """,
                job_id,
                json.dumps([entry]),
            )

    async def list_jobs(
        self, status: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[ScrapeJob], int]:
        """List scrape jobs with optional status filter."""
        conditions: list[str] = []
        params: list[object] = []
        idx = 1

        if status:
            conditions.append(f"status = ${idx}")
            params.append(status)
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        async with self._pool.acquire() as conn:
            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM scrape_jobs {where}", *params
            )
            rows = await conn.fetch(
                f"SELECT * FROM scrape_jobs {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
                *params,
                page_size,
                (page - 1) * page_size,
            )
            return [self._row_to_job(r) for r in rows], total or 0

    @staticmethod
    def _row_to_job(row: asyncpg.Record) -> ScrapeJob:
        """Convert a database row to a ScrapeJob model."""
        data = dict(row)
        if isinstance(data.get("agent_log"), str):
            data["agent_log"] = json.loads(data["agent_log"])
        if isinstance(data.get("error_details"), str):
            data["error_details"] = json.loads(data["error_details"])
        return ScrapeJob(**data)
