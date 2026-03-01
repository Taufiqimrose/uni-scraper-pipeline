from uuid import UUID

from pydantic import BaseModel

from .enums import DegreeType, ScrapeStatus


# ── Request Schemas ──────────────────────────────────────────────


class ScrapeRequest(BaseModel):
    url: str
    university_name: str
    force_rescrape: bool = False
    catalog_year: str | None = None


class UniversityQuery(BaseModel):
    search: str | None = None
    state: str | None = None
    page: int = 1
    page_size: int = 20


# ── Response Schemas ─────────────────────────────────────────────


class ScrapeJobResponse(BaseModel):
    job_id: UUID
    status: ScrapeStatus
    progress: float
    current_step: str | None
    programs_found: int
    programs_scraped: int
    courses_found: int
    error_message: str | None = None


class UniversityResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    domain: str
    catalog_url: str
    logo_url: str | None
    program_count: int
    last_scraped_at: str | None


class ProgramListItem(BaseModel):
    id: UUID
    name: str
    degree_type: DegreeType
    department: str | None
    total_units: int | None


class PrerequisiteResponse(BaseModel):
    course_code: str
    is_corequisite: bool
    group_id: int
    notes: str | None = None


class CourseInRequirement(BaseModel):
    code: str
    title: str
    units: int
    is_required: bool
    alternatives: list[str]
    prerequisites: list[str]


class RequirementGroupResponse(BaseModel):
    name: str
    type: str
    units_required: int | None
    courses: list[CourseInRequirement]


class ProgramDetailResponse(BaseModel):
    id: UUID
    name: str
    degree_type: DegreeType
    department: str | None
    description: str | None
    total_units: int | None
    source_url: str
    requirement_groups: list[RequirementGroupResponse]


class CourseDetailResponse(BaseModel):
    id: UUID
    code: str
    title: str
    description: str | None
    units: int
    prerequisites: list[PrerequisiteResponse]
    programs: list[str]


class PaginatedResponse(BaseModel):
    items: list  # type: ignore[type-arg]
    total: int
    page: int
    page_size: int
    has_more: bool
