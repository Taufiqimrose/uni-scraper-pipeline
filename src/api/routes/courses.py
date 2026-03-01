from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.db.repositories import CourseRepository
from src.models import CourseDetailResponse, PaginatedResponse

from ..dependencies import get_course_repo, verify_api_key

router = APIRouter(tags=["courses"], dependencies=[Depends(verify_api_key)])


@router.get("/universities/{university_id}/courses", response_model=PaginatedResponse)
async def list_courses(
    university_id: UUID,
    repo: Annotated[CourseRepository, Depends(get_course_repo)],
    department: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse:
    """List catalog courses for a university."""
    courses, total = await repo.list_by_university(
        university_id=university_id,
        department=department,
        search=search,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[
            CourseDetailResponse(
                id=c.id,
                code=c.code,
                title=c.title,
                description=c.description,
                units=c.units,
                prerequisites=[],
                programs=[],
            )
            for c in courses
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/courses/{course_id}", response_model=CourseDetailResponse)
async def get_course(
    course_id: UUID,
    repo: Annotated[CourseRepository, Depends(get_course_repo)],
) -> CourseDetailResponse:
    """Get a course with prerequisites and program references."""
    course = await repo.get_by_id(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # TODO: Load prerequisites and program references
    return CourseDetailResponse(
        id=course.id,
        code=course.code,
        title=course.title,
        description=course.description,
        units=course.units,
        prerequisites=[],
        programs=[],
    )
