import json

import structlog
from openai import AsyncOpenAI

from src.models import ProgramDetail, ValidationReport

from .prompts.system import AGENT_IDENTITY, JSON_INSTRUCTIONS
from .prompts.validation import VALIDATION_PROMPT

logger = structlog.get_logger()


class ValidatorAgent:
    """Validates extraction completeness and data quality."""

    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o") -> None:
        self._client = client
        self._model = model

    async def validate(
        self,
        programs: list[ProgramDetail],
        university_name: str,
        estimated_program_count: int,
    ) -> tuple[ValidationReport, int]:
        """Validate extracted data for completeness and quality.

        Returns:
            Tuple of (ValidationReport, tokens_used)
        """
        # Build summary statistics
        all_course_codes: set[str] = set()
        all_prereqs: set[str] = set()
        zero_course_programs: list[str] = []

        for program in programs:
            total_courses = sum(len(rg.courses) for rg in program.requirements)
            if total_courses == 0:
                zero_course_programs.append(program.name)
            for rg in program.requirements:
                for course in rg.courses:
                    all_course_codes.add(course.code)
                    all_prereqs.update(course.prerequisites)

        # Build sample program summaries (first 10)
        sample_lines = []
        for p in programs[:10]:
            course_count = sum(len(rg.courses) for rg in p.requirements)
            sample_lines.append(f"  - {p.name} ({p.degree_type}): {course_count} courses, {p.total_units or '?'} units")

        prompt = VALIDATION_PROMPT.format(
            university_name=university_name,
            total_programs=len(programs),
            total_courses=len(all_course_codes),
            estimated_programs=estimated_program_count,
            zero_course_programs=", ".join(zero_course_programs) or "None",
            sample_programs="\n".join(sample_lines),
            all_prerequisites=", ".join(sorted(all_prereqs)[:100]),
            all_course_codes=", ".join(sorted(all_course_codes)[:100]),
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": f"{AGENT_IDENTITY}\n\n{JSON_INSTRUCTIONS}"},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=4096,
        )

        content = response.choices[0].message.content or "{}"
        total_tokens = response.usage.total_tokens if response.usage else 0

        data = json.loads(content)
        report = ValidationReport(**data)

        logger.info(
            "validator_complete",
            is_valid=report.is_valid,
            completeness=report.completeness_score,
            issues=len(report.issues),
            tokens=total_tokens,
        )
        return report, total_tokens

    def quick_validate(self, programs: list[ProgramDetail]) -> ValidationReport:
        """Fast local validation without LLM call."""
        issues = []
        all_codes: set[str] = set()
        all_prereqs: set[str] = set()

        for program in programs:
            total_courses = sum(len(rg.courses) for rg in program.requirements)
            if total_courses == 0:
                issues.append({
                    "severity": "error",
                    "message": f"Program '{program.name}' has zero courses",
                    "program_name": program.name,
                    "course_code": None,
                })
            for rg in program.requirements:
                for course in rg.courses:
                    all_codes.add(course.code)
                    all_prereqs.update(course.prerequisites)

        orphaned = all_prereqs - all_codes
        if orphaned:
            for code in list(orphaned)[:20]:
                issues.append({
                    "severity": "warning",
                    "message": f"Prerequisite '{code}' not found in extracted courses",
                    "program_name": None,
                    "course_code": code,
                })

        completeness = 1.0 if not issues else max(0.0, 1.0 - len(issues) * 0.05)

        from src.models import ValidationIssue
        return ValidationReport(
            is_valid=len([i for i in issues if i["severity"] == "error"]) == 0,
            completeness_score=completeness,
            issues=[ValidationIssue(**i) for i in issues],
            orphaned_prerequisites=list(orphaned),
        )
