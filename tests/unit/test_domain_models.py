import pytest
from pydantic import ValidationError

from src.models import (
    AgentState,
    Course,
    DegreeType,
    DiscoveredProgram,
    NavigationPlan,
    Program,
    ScrapeJob,
    ScrapeStatus,
    SiteType,
    University,
)


class TestUniversity:
    def test_create_university(self) -> None:
        uni = University(
            name="Sacramento State",
            slug="sacramento-state",
            domain="csus.edu",
            catalog_url="https://catalog.csus.edu",
        )
        assert uni.name == "Sacramento State"
        assert uni.country == "US"
        assert uni.program_count == 0

    def test_university_with_all_fields(self) -> None:
        uni = University(
            name="MIT",
            slug="mit",
            domain="mit.edu",
            catalog_url="https://catalog.mit.edu",
            state="MA",
            program_count=150,
        )
        assert uni.state == "MA"
        assert uni.program_count == 150


class TestProgram:
    def test_create_program(self) -> None:
        from uuid import uuid4

        prog = Program(
            university_id=uuid4(),
            name="Computer Science",
            degree_type=DegreeType.BS,
            source_url="https://catalog.csus.edu/programs/cs",
        )
        assert prog.degree_type == DegreeType.BS
        assert prog.is_active is True


class TestCourse:
    def test_create_course(self) -> None:
        from uuid import uuid4

        course = Course(
            university_id=uuid4(),
            code="CSC 130",
            title="Data Structures",
            units=3,
        )
        assert course.code == "CSC 130"
        assert course.units == 3


class TestScrapeJob:
    def test_default_status(self) -> None:
        job = ScrapeJob(
            university_name="Test University",
            seed_url="https://test.edu",
        )
        assert job.status == ScrapeStatus.QUEUED
        assert job.progress == 0.0


class TestNavigationPlan:
    def test_create_plan(self) -> None:
        plan = NavigationPlan(
            site_type=SiteType.CATALOG_SYSTEM,
            catalog_root="https://catalog.csus.edu",
            program_list_urls=["https://catalog.csus.edu/programs"],
            estimated_program_count=120,
            navigation_strategy="alphabetical_index",
        )
        assert plan.site_type == SiteType.CATALOG_SYSTEM
        assert len(plan.program_list_urls) == 1


class TestDiscoveredProgram:
    def test_create_discovered_program(self) -> None:
        prog = DiscoveredProgram(
            name="Computer Science",
            url="https://catalog.csus.edu/programs/cs",
            degree_type=DegreeType.BS,
            confidence=0.95,
        )
        assert prog.confidence == 0.95


class TestAgentState:
    def test_has_budget(self) -> None:
        state = AgentState(
            job_id="test",
            seed_url="https://test.edu",
            university_name="Test",
            token_budget=1000,
        )
        assert state.has_budget() is True
        state.total_tokens_used = 1001
        assert state.has_budget() is False

    def test_log_decision(self) -> None:
        from src.models import AgentPhase

        state = AgentState(
            job_id="test",
            seed_url="https://test.edu",
            university_name="Test",
        )
        state.log_decision(AgentPhase.PLANNING, "test_action", "test_reasoning")
        assert len(state.decisions) == 1
        assert state.decisions[0].action == "test_action"
