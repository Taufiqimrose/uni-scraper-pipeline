import asyncio

import structlog

from src.db.connection import get_pool
from src.db.repositories import ScrapeJobRepository
from src.models import ScrapeRequest, ScrapeStatus

from .job_manager import JobManager

logger = structlog.get_logger()


class BackgroundWorker:
    """Background worker that polls for queued jobs and processes them."""

    def __init__(self, poll_interval: float = 5.0) -> None:
        self._poll_interval = poll_interval
        self._running = False
        self._job_manager = JobManager()

    async def start(self) -> None:
        """Start the worker loop."""
        self._running = True
        logger.info("worker_started")

        while self._running:
            try:
                await self._poll_and_process()
            except Exception as e:
                logger.error("worker_poll_error", error=str(e))

            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        """Stop the worker loop."""
        self._running = False
        logger.info("worker_stopped")

    async def _poll_and_process(self) -> None:
        """Check for queued jobs and process the next one."""
        pool = await get_pool()
        repo = ScrapeJobRepository(pool)

        jobs, _ = await repo.list_jobs(status="queued", page=1, page_size=1)
        if not jobs:
            return

        job = jobs[0]
        logger.info("worker_processing_job", job_id=str(job.id))

        request = ScrapeRequest(
            url=job.seed_url,
            university_name=job.university_name,
        )

        try:
            await self._job_manager.process_job(str(job.id), request)
        except Exception as e:
            logger.error("worker_job_failed", job_id=str(job.id), error=str(e))
            await repo.update_status(
                job.id, ScrapeStatus.FAILED, error_message=str(e)
            )
