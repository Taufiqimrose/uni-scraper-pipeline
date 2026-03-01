from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.db.repositories import UniversityRepository
from src.models import PaginatedResponse, UniversityResponse

from ..dependencies import get_university_repo, verify_api_key

router = APIRouter(tags=["universities"], dependencies=[Depends(verify_api_key)])


@router.get("/universities", response_model=PaginatedResponse)
async def list_universities(
    repo: Annotated[UniversityRepository, Depends(get_university_repo)],
    search: str | None = None,
    state: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse:
    """List all scraped universities."""
    universities, total = await repo.list(search=search, state=state, page=page, page_size=page_size)
    return PaginatedResponse(
        items=[
            UniversityResponse(
                id=u.id,
                name=u.name,
                slug=u.slug,
                domain=u.domain,
                catalog_url=u.catalog_url,
                logo_url=u.logo_url,
                program_count=u.program_count,
                last_scraped_at=u.last_scraped_at.isoformat() if u.last_scraped_at else None,
            )
            for u in universities
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/universities/{id_or_slug}", response_model=UniversityResponse)
async def get_university(
    id_or_slug: str,
    repo: Annotated[UniversityRepository, Depends(get_university_repo)],
) -> UniversityResponse:
    """Get a university by ID or slug."""
    # Try UUID first, fall back to slug
    try:
        uid = UUID(id_or_slug)
        university = await repo.get_by_id(uid)
    except ValueError:
        university = await repo.get_by_slug(id_or_slug)

    if not university:
        raise HTTPException(status_code=404, detail="University not found")

    return UniversityResponse(
        id=university.id,
        name=university.name,
        slug=university.slug,
        domain=university.domain,
        catalog_url=university.catalog_url,
        logo_url=university.logo_url,
        program_count=university.program_count,
        last_scraped_at=university.last_scraped_at.isoformat() if university.last_scraped_at else None,
    )
