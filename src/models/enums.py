from enum import Enum


class DegreeType(str, Enum):
    BS = "BS"
    BA = "BA"
    BFA = "BFA"
    MS = "MS"
    MA = "MA"
    MBA = "MBA"
    PHD = "PhD"
    CERTIFICATE = "Certificate"
    MINOR = "Minor"
    ASSOCIATE = "Associate"
    OTHER = "Other"


class RequirementType(str, Enum):
    CORE = "core"
    ELECTIVE = "elective"
    GENERAL_ED = "general_education"
    MAJOR_PREP = "major_preparation"
    CAPSTONE = "capstone"
    CONCENTRATION = "concentration"
    FREE_ELECTIVE = "free_elective"


class ScrapeStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DISCOVERING = "discovering"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class AgentPhase(str, Enum):
    INITIALIZING = "initializing"
    PLANNING = "planning"
    DISCOVERING_PROGRAMS = "discovering_programs"
    EXTRACTING_PROGRAMS = "extracting_programs"
    ENRICHING_COURSES = "enriching_courses"
    VALIDATING = "validating"
    STORING = "storing"
    COMPLETE = "complete"
    FAILED = "failed"


class SiteType(str, Enum):
    CATALOG_SYSTEM = "catalog_system"
    DEPARTMENT_PAGES = "department_pages"
    SINGLE_PAGE = "single_page_catalog"
    SEARCH_BASED = "search_based"
    API_DRIVEN = "api_driven"
    UNKNOWN = "unknown"
