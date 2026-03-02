from uuid import UUID

from pydantic import BaseModel, model_validator

from .enums import DegreeType, ScrapeStatus


# ── Request Schemas ──────────────────────────────────────────────


class ScrapeRequest(BaseModel):
    url: str | None = None
    university_name: str
    major_name: str | None = None
    force_rescrape: bool = False
    catalog_year: str | None = None

    @model_validator(mode="after")
    def validate_request_type(self) -> "ScrapeRequest":
        """Require either a URL or a major_name for targeted search."""
        if not self.url and not self.major_name:
            raise ValueError(
                "Provide either 'url' for direct scraping or 'major_name' for search-based scraping"
            )
        return self


class SearchRequest(BaseModel):
    """Request to resolve a university + major into catalog URLs (preview, no scraping)."""

    university_name: str
    major_name: str | None = None


class SearchResultResponse(BaseModel):
    """Response from the search/resolve endpoint."""

    catalog_url: str
    program_url: str | None
    university_name_normalized: str
    confidence: float


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


class PipelineStep(BaseModel):
    """A single step in the scraping pipeline."""

    name: str
    status: str  # "completed" | "running" | "pending" | "failed" | "skipped"
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float | None = None
    detail: str | None = None


class PipelineStatusResponse(BaseModel):
    """Structured pipeline view of a scrape job — shows each step with timing and metrics."""

    job_id: UUID
    university_name: str
    major_name: str | None = None
    overall_status: ScrapeStatus
    progress: float
    steps: list[PipelineStep]
    metrics: dict  # type: ignore[type-arg]
    started_at: str | None = None
    elapsed_seconds: float | None = None


class PaginatedResponse(BaseModel):
    items: list  # type: ignore[type-arg]
    total: int
    page: int
    page_size: int
    has_more: bool
