from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .enums import DegreeType, RequirementType, ScrapeStatus


class University(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    slug: str
    domain: str
    catalog_url: str
    logo_url: str | None = None
    state: str | None = None
    country: str = "US"
    program_count: int = 0
    last_scraped_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Program(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    university_id: UUID
    name: str
    degree_type: DegreeType
    department: str | None = None
    description: str | None = None
    source_url: str
    total_units: int | None = None
    catalog_year: str | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Course(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    university_id: UUID
    code: str
    title: str
    description: str | None = None
    units: int
    department: str | None = None
    source_url: str | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Prerequisite(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    course_id: UUID
    prerequisite_course_id: UUID | None = None
    prerequisite_code: str
    is_corequisite: bool = False
    group_id: int = 0
    notes: str | None = None


class RequirementGroup(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    program_id: UUID
    name: str
    type: RequirementType
    units_required: int | None = None
    courses_required: int | None = None
    sort_order: int = 0
    notes: str | None = None


class ProgramRequirement(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    requirement_group_id: UUID
    course_id: UUID | None = None
    course_code: str
    course_title: str
    units: int
    is_required: bool = True
    alternatives: list[str] = Field(default_factory=list)
    sort_order: int = 0
    notes: str | None = None


class ScrapeJob(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    university_name: str
    seed_url: str
    major_name: str | None = None
    search_type: str = "direct_url"  # "direct_url" | "search"
    status: ScrapeStatus = ScrapeStatus.QUEUED
    progress: float = 0.0
    current_step: str | None = None
    programs_found: int = 0
    programs_scraped: int = 0
    courses_found: int = 0
    error_message: str | None = None
    error_details: dict | None = None  # type: ignore[type-arg]
    agent_log: list[dict] = Field(default_factory=list)  # type: ignore[type-arg]
    total_tokens_used: int = 0
    total_pages_fetched: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
