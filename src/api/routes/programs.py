from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.db.repositories import ProgramRepository
from src.models import PaginatedResponse, ProgramDetailResponse, ProgramListItem

from ..dependencies import get_program_repo, verify_api_key

router = APIRouter(tags=["programs"], dependencies=[Depends(verify_api_key)])


@router.get("/universities/{university_id}/programs", response_model=PaginatedResponse)
async def list_programs(
    university_id: UUID,
    repo: Annotated[ProgramRepository, Depends(get_program_repo)],
    degree_type: str | None = None,
    department: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse:
    """List programs for a university."""
    programs, total = await repo.list_by_university(
        university_id=university_id,
        degree_type=degree_type,
        department=department,
        search=search,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[
            ProgramListItem(
                id=p.id,
                name=p.name,
                degree_type=p.degree_type,
                department=p.department,
                total_units=p.total_units,
            )
            for p in programs
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/programs/{program_id}", response_model=ProgramDetailResponse)
async def get_program(
    program_id: UUID,
    repo: Annotated[ProgramRepository, Depends(get_program_repo)],
) -> ProgramDetailResponse:
    """Get a program with full requirement details."""
    program = await repo.get_by_id(program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # TODO: Load requirement groups and courses from DB
    return ProgramDetailResponse(
        id=program.id,
        name=program.name,
        degree_type=program.degree_type,
        department=program.department,
        description=program.description,
        total_units=program.total_units,
        source_url=program.source_url,
        requirement_groups=[],
    )
