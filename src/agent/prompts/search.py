"""Prompts for search resolution and program finding."""

URL_RESOLUTION_PROMPT = """Given these Google search results, identify the best URL for a university's academic catalog.

University: {university_name}
Target Major: {major_name}

Search Results:
{search_results}

Your task:
1. Find the official university catalog/academic programs URL (NOT a news article, NOT Wikipedia, NOT a third-party site)
2. If a target major was specified, also find the direct URL to that major's program page if one appears in the results
3. Normalize the university name to its official form

<schema>
{{
    "catalog_url": "The main catalog or academic programs URL (REQUIRED)",
    "program_url": "Direct URL to the target major's page if found (or null)",
    "university_name_normalized": "Official university name (e.g., 'Massachusetts Institute of Technology')",
    "confidence": 0.95
}}
</schema>

Rules:
- catalog_url MUST be from the university's official domain (e.g., .edu)
- Prefer catalog/academic program URLs over general university homepages
- If you see a direct link to the target major's requirements page, include it as program_url
- confidence should reflect how sure you are this is the right catalog (0.0 to 1.0)
- If no good result exists, set catalog_url to empty string"""

FIND_PROGRAM_PROMPT = """Find the link to the "{major_name}" program/major on this university catalog page.

University: {university_name}
Target Major: {major_name}

Look for:
- A direct link to the "{major_name}" program, major, or degree page
- Links containing related keywords (e.g., for "Computer Science" look for "CS", "Computing", "Computer Science, B.S.")
- Navigation links that would lead to the target program

<schema>
{{
    "program_url": "Direct URL to the target major's page (or null if not found)",
    "program_name_on_page": "The exact name as it appears on the page",
    "confidence": 0.9,
    "alternative_urls": ["Other URLs that might lead to the program"],
    "notes": "Any observations about finding the program"
}}
</schema>

<context>
Page URL: {page_url}
</context>

<page_content>
{page_content}
</page_content>"""
