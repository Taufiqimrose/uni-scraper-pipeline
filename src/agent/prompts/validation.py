"""Prompts for the Validator agent - checking extraction completeness."""

VALIDATION_PROMPT = """Review this extraction summary and identify any issues or gaps.

Check for:
1. Programs with zero courses (likely extraction failure)
2. Prerequisites that reference non-existent course codes
3. Unit count inconsistencies (course units don't sum to program total)
4. Duplicate programs or courses
5. Missing data (programs with no department, courses with 0 units)
6. Coverage: does the extracted count match the estimated total?

<schema>
{{
    "is_valid": true/false,
    "completeness_score": 0.95,
    "issues": [
        {{
            "severity": "error | warning | info",
            "message": "Description of the issue",
            "program_name": "Program Name or null",
            "course_code": "CSC 130 or null"
        }}
    ],
    "missing_programs": ["Program names that seem to be missing"],
    "orphaned_prerequisites": ["Course codes referenced as prereqs but not in course list"],
    "recommendations": ["Suggested actions to improve data quality"]
}}
</schema>

<extraction_summary>
University: {university_name}
Total programs extracted: {total_programs}
Total courses extracted: {total_courses}
Estimated programs (from planning): {estimated_programs}

Programs with zero courses: {zero_course_programs}

Sample programs:
{sample_programs}

All course codes referenced as prerequisites:
{all_prerequisites}

All extracted course codes:
{all_course_codes}
</extraction_summary>"""
