import hashlib
from datetime import datetime
from uuid import uuid4

import asyncpg
import structlog
from openai import AsyncOpenAI

from src.browser.html_cleaner import HtmlCleaner
from src.browser.manager import BrowserManager
from src.browser.page_fetcher import FetchResult, PageFetcher
from src.browser.rate_limiter import RateLimiter
from src.browser.robots_checker import RobotsChecker
from src.cache.page_cache import PageCache
from src.db.repositories import CourseRepository, ProgramRepository, ScrapeJobRepository, UniversityRepository
from src.models import (
    AgentPhase,
    AgentState,
    Course,
    PageVisit,
    Program,
    ProgramDetail,
    ScrapeStatus,
    University,
)
from src.utils.url_utils import extract_domain, slugify

from .extractor import ExtractorAgent
from .navigator import NavigatorAgent
from .planner import PlannerAgent
from .validator import ValidatorAgent

logger = structlog.get_logger()


class Orchestrator:
    """Top-level agent loop: Plan -> Execute -> Observe for scraping a university."""

    def __init__(
        self,
        openai_client: AsyncOpenAI,
        db_pool: asyncpg.Pool,
        browser_manager: BrowserManager,
        model: str = "gpt-4o",
        token_budget: int = 2_000_000,
        rate_limit_delay: float = 2.0,
        cache_ttl_hours: int = 24,
        page_timeout_ms: int = 30_000,
    ) -> None:
        self._openai = openai_client
        self._db_pool = db_pool
        self._browser = browser_manager

        # Agents
        self._planner = PlannerAgent(openai_client, model)
        self._navigator = NavigatorAgent(openai_client, model)
        self._extractor = ExtractorAgent(openai_client, model)
        self._validator = ValidatorAgent(openai_client, model)

        # Browser tools
        self._rate_limiter = RateLimiter(rate_limit_delay)
        self._robots_checker = RobotsChecker()
        self._html_cleaner = HtmlCleaner()
        self._page_fetcher = PageFetcher(
            self._rate_limiter, self._robots_checker, self._html_cleaner, page_timeout_ms
        )

        # Cache + repos
        self._cache = PageCache(db_pool, cache_ttl_hours)
        self._job_repo = ScrapeJobRepository(db_pool)
        self._uni_repo = UniversityRepository(db_pool)
        self._program_repo = ProgramRepository(db_pool)
        self._course_repo = CourseRepository(db_pool)

        self._token_budget = token_budget

    async def run(self, job_id: str, seed_url: str, university_name: str) -> None:
        """Execute the full scraping pipeline for a university."""
        state = AgentState(
            job_id=job_id,
            seed_url=seed_url,
            university_name=university_name,
            token_budget=self._token_budget,
        )

        try:
            await self._update_job(state, ScrapeStatus.RUNNING, "Initializing")

            # Phase 1: Planning
            await self._phase_planning(state)

            # Phase 2: Discover programs
            await self._phase_discovery(state)

            # Phase 3: Extract program details
            await self._phase_extraction(state)

            # Phase 4: Validate
            await self._phase_validation(state)

            # Phase 5: Store
            await self._phase_storage(state)

            # Complete
            status = ScrapeStatus.COMPLETED if state.phase != AgentPhase.FAILED else ScrapeStatus.PARTIAL
            await self._update_job(state, status, "Complete")

            logger.info(
                "pipeline_complete",
                job_id=job_id,
                programs=len(state.extracted_programs),
                tokens_used=state.total_tokens_used,
                pages_fetched=state.total_pages_fetched,
            )

        except Exception as e:
            logger.error("pipeline_failed", job_id=job_id, error=str(e))
            await self._update_job(
                state, ScrapeStatus.FAILED, "Failed", error_message=str(e)
            )
            raise

    async def _phase_planning(self, state: AgentState) -> None:
        """Phase 1: Analyze the seed URL and create a navigation plan."""
        state.phase = AgentPhase.PLANNING
        await self._update_job(state, ScrapeStatus.DISCOVERING, "Analyzing site structure")

        # Fetch the seed page
        result = await self._fetch_page(state, state.seed_url)
        if not result:
            raise RuntimeError(f"Could not fetch seed URL: {state.seed_url}")

        # Ask the planner to analyze the site
        plan, tokens = await self._planner.plan(
            result.cleaned_html, state.university_name, state.seed_url
        )
        state.total_tokens_used += tokens

        # Update state with plan results
        state.catalog_root = plan.catalog_root
        state.site_type = plan.site_type
        state.navigation_strategy = plan.navigation_strategy
        state.urls_to_visit = list(plan.program_list_urls)

        state.log_decision(
            AgentPhase.PLANNING,
            "site_analyzed",
            f"Site type: {plan.site_type}, Strategy: {plan.navigation_strategy}",
            f"Found {len(plan.program_list_urls)} program list URLs, estimated {plan.estimated_program_count} programs",
        )

    async def _phase_discovery(self, state: AgentState) -> None:
        """Phase 2: Visit program list pages and discover all program URLs."""
        state.phase = AgentPhase.DISCOVERING_PROGRAMS
        await self._update_job(state, ScrapeStatus.DISCOVERING, "Discovering programs")

        visited_urls: set[str] = set()

        while state.urls_to_visit and state.has_budget():
            url = state.urls_to_visit.pop(0)
            if url in visited_urls:
                continue
            visited_urls.add(url)

            result = await self._fetch_page(state, url)
            if not result:
                continue

            programs, pagination_urls, tokens = await self._navigator.discover_programs(
                result.cleaned_html,
                state.university_name,
                url,
                len(state.discovered_programs),
            )
            state.total_tokens_used += tokens

            # Add discovered programs
            seen_urls = {p.url for p in state.discovered_programs}
            for prog in programs:
                if prog.url not in seen_urls:
                    state.discovered_programs.append(prog)
                    state.discovered_program_urls.append(prog.url)
                    seen_urls.add(prog.url)

            # Add pagination URLs
            for purl in pagination_urls:
                if purl not in visited_urls:
                    state.urls_to_visit.append(purl)

            await self._update_job(
                state,
                ScrapeStatus.DISCOVERING,
                f"Discovering programs ({len(state.discovered_programs)} found)",
                programs_found=len(state.discovered_programs),
            )

        logger.info(
            "discovery_complete",
            total_programs=len(state.discovered_programs),
            pages_visited=len(visited_urls),
        )

    async def _phase_extraction(self, state: AgentState) -> None:
        """Phase 3: Extract detailed data from each program page."""
        state.phase = AgentPhase.EXTRACTING_PROGRAMS
        total = len(state.discovered_programs)

        for i, discovered in enumerate(state.discovered_programs):
            if not state.has_budget():
                logger.warning("token_budget_exhausted", extracted=i, total=total)
                break

            await self._update_job(
                state,
                ScrapeStatus.EXTRACTING,
                f"Extracting program {i + 1}/{total}: {discovered.name}",
                programs_scraped=i,
                progress=i / total if total > 0 else 0,
            )

            try:
                result = await self._fetch_page(state, discovered.url)
                if not result:
                    state.failed_urls[discovered.url] = "Failed to fetch page"
                    continue

                program_detail, tokens = await self._extractor.extract_program(
                    result.cleaned_html, state.university_name, discovered.url
                )
                state.total_tokens_used += tokens
                state.extracted_programs.append(program_detail)

                # Track courses
                for rg in program_detail.requirements:
                    for course in rg.courses:
                        state.extracted_courses[course.code] = {
                            "code": course.code,
                            "title": course.title,
                            "units": course.units,
                        }
                        if course.prerequisites:
                            state.prerequisite_map[course.code] = course.prerequisites

            except Exception as e:
                logger.error(
                    "extraction_failed",
                    program=discovered.name,
                    url=discovered.url,
                    error=str(e),
                )
                state.failed_urls[discovered.url] = str(e)

        logger.info(
            "extraction_complete",
            extracted=len(state.extracted_programs),
            failed=len(state.failed_urls),
            total=total,
        )

    async def _phase_validation(self, state: AgentState) -> None:
        """Phase 4: Validate extracted data quality."""
        state.phase = AgentPhase.VALIDATING
        await self._update_job(state, ScrapeStatus.VALIDATING, "Validating extracted data")

        # Quick local validation first
        report = self._validator.quick_validate(state.extracted_programs)

        logger.info(
            "validation_complete",
            is_valid=report.is_valid,
            completeness=report.completeness_score,
            issues=len(report.issues),
        )

        state.log_decision(
            AgentPhase.VALIDATING,
            "validation_complete",
            f"Completeness: {report.completeness_score:.0%}, Issues: {len(report.issues)}",
            f"Valid: {report.is_valid}",
        )

    async def _phase_storage(self, state: AgentState) -> None:
        """Phase 5: Store extracted data in the database."""
        state.phase = AgentPhase.STORING
        await self._update_job(state, ScrapeStatus.EXTRACTING, "Storing data")

        domain = extract_domain(state.seed_url)
        slug = slugify(state.university_name)

        # Upsert university
        university = University(
            name=state.university_name,
            slug=slug,
            domain=domain,
            catalog_url=state.seed_url,
            program_count=len(state.extracted_programs),
            last_scraped_at=datetime.utcnow(),
        )
        university = await self._uni_repo.upsert(university)

        # Upsert courses
        course_id_map: dict[str, str] = {}
        for code, info in state.extracted_courses.items():
            course = Course(
                university_id=university.id,
                code=code,
                title=info["title"],
                units=info["units"],
            )
            saved = await self._course_repo.upsert(course)
            course_id_map[code] = str(saved.id)

        # Upsert programs
        for program_detail in state.extracted_programs:
            program = Program(
                university_id=university.id,
                name=program_detail.name,
                degree_type=program_detail.degree_type,
                department=program_detail.department,
                description=program_detail.description,
                source_url=state.seed_url,
                total_units=program_detail.total_units,
            )
            await self._program_repo.upsert(program)

        logger.info(
            "storage_complete",
            university=university.slug,
            programs=len(state.extracted_programs),
            courses=len(course_id_map),
        )

    async def _fetch_page(self, state: AgentState, url: str) -> FetchResult | None:
        """Fetch a page with caching and error handling."""
        # Check cache first
        cached = await self._cache.get(url)
        if cached:
            content_hash = hashlib.sha256(cached.encode()).hexdigest()
            state.pages_visited.append(
                PageVisit(
                    url=url,
                    fetched_at=datetime.utcnow(),
                    page_type="cached",
                    content_hash=content_hash,
                )
            )
            return FetchResult(
                url=url,
                raw_html=cached,
                cleaned_html=cached,
                content_hash=content_hash,
                status_code=200,
            )

        # Fetch live
        try:
            ctx_wrapper = await self._browser.new_context()
            async with ctx_wrapper as context:
                result = await self._page_fetcher.fetch(url, context)

            state.total_pages_fetched += 1
            state.pages_visited.append(
                PageVisit(
                    url=url,
                    fetched_at=datetime.utcnow(),
                    page_type="live",
                    content_hash=result.content_hash,
                )
            )

            # Cache the result
            await self._cache.set(url, result.cleaned_html, result.content_hash)

            return result

        except Exception as e:
            logger.error("fetch_failed", url=url, error=str(e))
            retries = state.retry_counts.get(url, 0)
            if retries < 2:
                state.retry_counts[url] = retries + 1
                state.urls_to_visit.append(url)
            else:
                state.failed_urls[url] = str(e)
            return None

    async def _update_job(
        self,
        state: AgentState,
        status: ScrapeStatus,
        step: str,
        *,
        programs_found: int | None = None,
        programs_scraped: int | None = None,
        progress: float | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update the scrape job in the database."""
        from uuid import UUID

        await self._job_repo.update_status(
            UUID(state.job_id),
            status,
            current_step=step,
            programs_found=programs_found or len(state.discovered_programs),
            programs_scraped=programs_scraped or len(state.extracted_programs),
            courses_found=len(state.extracted_courses),
            progress=progress,
            error_message=error_message,
            total_tokens_used=state.total_tokens_used,
            total_pages_fetched=state.total_pages_fetched,
        )
