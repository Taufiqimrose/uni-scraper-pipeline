"""Prompts for the Navigator agent - discovering program links."""

NAVIGATION_PROMPT = """Extract all links to individual academic programs (majors, minors, certificates, degrees) from this page.

For each program found, provide:
- name: The program name (e.g., "Computer Science", "Business Administration")
- url: The full URL to the program's detail page
- degree_type: One of BS, BA, BFA, MS, MA, MBA, PhD, Certificate, Minor, Associate, Other
- department: The department if visible (e.g., "Computer Science", "School of Business")
- confidence: How confident you are this is a real program (0.0 to 1.0)

Rules:
- Only include actual academic programs (not departments, offices, or general pages)
- Include ALL programs visible on this page, not just a few
- Use the full absolute URL, not relative paths
- If you see pagination or "next page" links, include them in a separate "pagination_urls" field

<schema>
{{
    "programs": [
        {{
            "name": "Program Name",
            "url": "https://...",
            "degree_type": "BS",
            "department": "Department Name or null",
            "confidence": 0.95
        }}
    ],
    "pagination_urls": ["URL to next page if exists"],
    "total_on_page": 0
}}
</schema>

<context>
University: {university_name}
Page URL: {page_url}
Programs found so far: {programs_found}
</context>

<page_content>
{page_content}
</page_content>"""

PAGE_CLASSIFICATION_PROMPT = """Classify this web page. What type of content does it contain?

Options:
- program_list: A page listing multiple academic programs/majors
- program_detail: A single program's detail page with requirements
- course_catalog: A page listing courses (not programs)
- department_page: A department's landing page
- index_page: An alphabetical or categorical index
- other: Something else entirely

<schema>
{{
    "page_type": "program_list | program_detail | course_catalog | department_page | index_page | other",
    "description": "Brief description of what this page contains",
    "has_program_links": true/false,
    "has_course_data": true/false,
    "recommended_action": "extract_programs | extract_courses | follow_links | skip"
}}
</schema>

<page_content>
{page_content}
</page_content>"""
