"""Prompts for the Extractor agent - extracting structured program data from HTML."""

EXTRACTION_PROMPT = """Extract complete program requirements from this university program page.

For this program, extract:
1. Basic info: name, degree type, department, description, total units
2. Requirement groups: logical sections like "Core Requirements", "Upper Division Electives", etc.
3. For each requirement group: list all courses with their codes, titles, unit counts
4. Mark whether each course is required or an elective choice
5. List any alternative courses (courses connected by "or")
6. Extract prerequisites for each course if listed

<schema>
{{
    "name": "Program Name",
    "degree_type": "BS | BA | BFA | MS | MA | MBA | PhD | Certificate | Minor | Associate | Other",
    "department": "Department Name or null",
    "description": "Brief program description or null",
    "total_units": 120,
    "requirements": [
        {{
            "name": "Requirement Group Name (e.g., Core Requirements)",
            "type": "core | elective | general_education | major_preparation | capstone | concentration | free_elective",
            "units_required": 30,
            "courses_required": null,
            "courses": [
                {{
                    "code": "CSC 130",
                    "title": "Data Structures and Algorithm Analysis",
                    "units": 3,
                    "is_required": true,
                    "prerequisites": ["CSC 20", "CSC 28"],
                    "corequisites": [],
                    "alternatives": [],
                    "notes": null
                }}
            ]
        }}
    ],
    "concentrations": ["Concentration Name 1"],
    "admission_requirements": "Description or null",
    "learning_outcomes": ["Outcome 1", "Outcome 2"]
}}
</schema>

Rules:
- Course codes should be in the format "DEPT NUM" (e.g., "CSC 130", "MATH 26A")
- Use null for units only when the page does not specify unit count; otherwise use the integer value
- If a group says "choose 3 from the following", mark those courses as is_required: false
- If courses are listed as alternatives (e.g., "CSC 130 or CSC 135"), put the alternative in the alternatives field
- Only extract data that is explicitly on the page - do not guess or infer
- total_units should be the program's stated total, or null if not specified

<context>
University: {university_name}
Program URL: {program_url}
</context>

<page_content>
{page_content}
</page_content>"""

EXTRACTION_RETRY_PROMPT = """Your previous extraction had issues. Please try again with corrections.

Issues found:
{issues}

Original page content:
<page_content>
{page_content}
</page_content>

Respond with the corrected JSON matching the schema above."""
