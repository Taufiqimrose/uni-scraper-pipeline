from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.config.settings import Settings, get_settings
from src.db.repositories import ScrapeJobRepository
from src.models import (
    PaginatedResponse,
    ScrapeJob,
    ScrapeJobResponse,
    ScrapeRequest,
    ScrapeStatus,
    SearchRequest,
    SearchResultResponse,
)
from src.queue.job_manager import JobManager
from src.search import SearchResolver, SerpClient

from ..dependencies import get_scrape_job_repo, verify_api_key

logger = structlog.get_logger()

router = APIRouter(tags=["scraping"], dependencies=[Depends(verify_api_key)])


@router.post("/search", response_model=SearchResultResponse)
async def search_university(
    request: SearchRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchResultResponse:
    """Resolve a university name (+ optional major) into catalog URLs.

    This is a preview/lookup endpoint — it does NOT start a scrape job.
    Use the returned URLs to verify before submitting to ``POST /scrape``.
    """
    from openai import AsyncOpenAI

    if not settings.SERP_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Search is unavailable: SERP_API_KEY is not configured.",
        )

    serp = SerpClient(api_key=settings.SERP_API_KEY)
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    resolver = SearchResolver(serp, openai_client, model=settings.OPENAI_MODEL)

    try:
        target = await resolver.resolve(request.university_name, request.major_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return SearchResultResponse(
        catalog_url=target.catalog_url,
        program_url=target.program_url,
        university_name_normalized=target.university_name_normalized,
        confidence=target.confidence,
    )


@router.post("/scrape", status_code=202, response_model=ScrapeJobResponse)
async def start_scrape(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    repo: Annotated[ScrapeJobRepository, Depends(get_scrape_job_repo)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ScrapeJobResponse:
    """Submit a new scraping job for a university.

    Two modes:

    1. **Direct URL** — provide ``url`` and ``university_name``.
    2. **Search-based** — provide ``university_name`` and ``major_name``.
       The pipeline will use SerpAPI + GPT-4o to find the catalog URL
       and scrape only the requested major.
    """
    seed_url = request.url
    search_type = "direct_url"

    # If no URL provided, resolve via search
    if not seed_url:
        if not settings.SERP_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="Search is unavailable: SERP_API_KEY is not configured.",
            )

        from openai import AsyncOpenAI

        serp = SerpClient(api_key=settings.SERP_API_KEY)
        openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resolver = SearchResolver(serp, openai_client, model=settings.OPENAI_MODEL)

        try:
            target = await resolver.resolve(request.university_name, request.major_name)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        seed_url = target.program_url or target.catalog_url
        search_type = "search"

        logger.info(
            "search_resolved_for_scrape",
            university=request.university_name,
            major=request.major_name,
            seed_url=seed_url,
            confidence=target.confidence,
        )

    job = ScrapeJob(
        university_name=request.university_name,
        seed_url=seed_url,
        major_name=request.major_name,
        search_type=search_type,
    )
    job = await repo.create(job)

    # Enqueue the job for background processing
    job_manager = JobManager()
    background_tasks.add_task(job_manager.process_job, str(job.id), request, seed_url)

    return ScrapeJobResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        programs_found=job.programs_found,
        programs_scraped=job.programs_scraped,
        courses_found=job.courses_found,
        error_message=job.error_message,
    )


@router.get("/scrape/{job_id}", response_model=ScrapeJobResponse)
async def get_scrape_status(
    job_id: UUID,
    repo: Annotated[ScrapeJobRepository, Depends(get_scrape_job_repo)],
) -> ScrapeJobResponse:
    """Get the status of a scraping job."""
    job = await repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return ScrapeJobResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        programs_found=job.programs_found,
        programs_scraped=job.programs_scraped,
        courses_found=job.courses_found,
        error_message=job.error_message,
    )


@router.get("/scrape/{job_id}/log")
async def get_scrape_log(
    job_id: UUID,
    repo: Annotated[ScrapeJobRepository, Depends(get_scrape_job_repo)],
) -> dict:  # type: ignore[type-arg]
    """Get the agent decision log for a scraping job."""
    job = await repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"agent_log": job.agent_log}


@router.delete("/scrape/{job_id}", status_code=204)
async def cancel_scrape(
    job_id: UUID,
    repo: Annotated[ScrapeJobRepository, Depends(get_scrape_job_repo)],
) -> None:
    """Cancel a running scraping job."""
    job = await repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in (ScrapeStatus.QUEUED, ScrapeStatus.RUNNING, ScrapeStatus.DISCOVERING, ScrapeStatus.EXTRACTING):
        raise HTTPException(status_code=400, detail="Job is not cancellable")
    await repo.update_status(job_id, ScrapeStatus.FAILED, error_message="Cancelled by user")


@router.get("/scrape", response_model=PaginatedResponse)
async def list_scrape_jobs(
    repo: Annotated[ScrapeJobRepository, Depends(get_scrape_job_repo)],
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse:
    """List all scraping jobs."""
    jobs, total = await repo.list_jobs(status=status, page=page, page_size=page_size)
    return PaginatedResponse(
        items=[
            ScrapeJobResponse(
                job_id=j.id,
                status=j.status,
                progress=j.progress,
                current_step=j.current_step,
                programs_found=j.programs_found,
                programs_scraped=j.programs_scraped,
                courses_found=j.courses_found,
                error_message=j.error_message,
            )
            for j in jobs
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )
