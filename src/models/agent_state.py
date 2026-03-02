from datetime import datetime

from pydantic import BaseModel, Field

from .enums import AgentPhase, DegreeType, SiteType


# ── Agent Planning Models ────────────────────────────────────────


class NavigationPlan(BaseModel):
    """Output from the Planner agent: how to navigate the university site."""

    site_type: SiteType
    catalog_root: str
    program_list_urls: list[str]
    estimated_program_count: int
    navigation_strategy: str
    notes: str = ""


class DiscoveredProgram(BaseModel):
    """A program/major discovered by the Navigator agent."""

    name: str
    url: str
    degree_type: DegreeType
    department: str | None = None
    confidence: float = 1.0


class CourseInfo(BaseModel):
    """A course extracted from a program page."""

    code: str
    title: str
    units: int
    is_required: bool = True
    prerequisites: list[str] = Field(default_factory=list)
    corequisites: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    notes: str | None = None


class ExtractedRequirementGroup(BaseModel):
    """A group of requirements extracted from a program page."""

    name: str
    type: str
    units_required: int | None = None
    courses_required: int | None = None
    courses: list[CourseInfo] = Field(default_factory=list)


class ProgramDetail(BaseModel):
    """Full program detail extracted by the Extractor agent."""

    name: str
    degree_type: DegreeType
    department: str | None = None
    description: str | None = None
    total_units: int | None = None
    requirements: list[ExtractedRequirementGroup] = Field(default_factory=list)
    concentrations: list[str] = Field(default_factory=list)
    admission_requirements: str | None = None
    learning_outcomes: list[str] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    """A single issue found during validation."""

    severity: str  # "error", "warning", "info"
    message: str
    program_name: str | None = None
    course_code: str | None = None


class ValidationReport(BaseModel):
    """Output from the Validator agent."""

    is_valid: bool
    completeness_score: float
    issues: list[ValidationIssue] = Field(default_factory=list)
    missing_programs: list[str] = Field(default_factory=list)
    orphaned_prerequisites: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# ── Agent State Machine ─────────────────────────────────────────


class PageVisit(BaseModel):
    """Record of a single page visit during scraping."""

    url: str
    fetched_at: datetime
    page_type: str
    content_hash: str
    tokens_used: int = 0


class AgentDecision(BaseModel):
    """A logged decision made by the agent."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    phase: AgentPhase
    action: str
    reasoning: str
    result: str | None = None


class AgentState(BaseModel):
    """Mutable state carried across the entire agent pipeline for one scrape job."""

    job_id: str
    seed_url: str
    university_name: str
    target_major: str | None = None  # For targeted single-major scraping
    phase: AgentPhase = AgentPhase.INITIALIZING

    # Discovery results
    catalog_root: str | None = None
    site_type: SiteType | None = None
    navigation_strategy: str | None = None

    # Accumulated data
    discovered_program_urls: list[str] = Field(default_factory=list)
    discovered_programs: list[DiscoveredProgram] = Field(default_factory=list)
    extracted_programs: list[ProgramDetail] = Field(default_factory=list)
    extracted_courses: dict[str, dict] = Field(default_factory=dict)  # type: ignore[type-arg]
    prerequisite_map: dict[str, list[str]] = Field(default_factory=dict)

    # Tracking
    pages_visited: list[PageVisit] = Field(default_factory=list)
    urls_to_visit: list[str] = Field(default_factory=list)
    failed_urls: dict[str, str] = Field(default_factory=dict)
    retry_counts: dict[str, int] = Field(default_factory=dict)

    # Metrics
    total_tokens_used: int = 0
    total_pages_fetched: int = 0
    token_budget: int = 2_000_000

    # Decision log
    decisions: list[AgentDecision] = Field(default_factory=list)

    def has_budget(self) -> bool:
        """Check if there is remaining token budget."""
        return self.total_tokens_used < self.token_budget

    def log_decision(self, phase: AgentPhase, action: str, reasoning: str, result: str | None = None) -> None:
        """Log an agent decision."""
        self.decisions.append(
            AgentDecision(phase=phase, action=action, reasoning=reasoning, result=result)
        )
