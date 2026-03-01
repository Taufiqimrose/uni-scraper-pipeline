"""Prompts for the Planner agent - site analysis and navigation planning."""

PLANNING_PROMPT = """Analyze this university website page and create a navigation plan for scraping all academic programs.

Your task:
1. Identify what kind of page this is (catalog home, department listing, program index, etc.)
2. Determine the site structure: how are programs/majors organized?
3. Find URLs that lead to program listings (alphabetical indexes, department pages, search pages)
4. Estimate how many programs/majors exist

<schema>
{{
    "site_type": "catalog_system | department_pages | single_page_catalog | search_based | api_driven | unknown",
    "catalog_root": "URL of the catalog root/home page",
    "program_list_urls": ["URL1", "URL2", "..."],
    "estimated_program_count": 0,
    "navigation_strategy": "Description of how to navigate: alphabetical_index, department_drill_down, search_api, single_page_scan, etc.",
    "notes": "Any observations about the site structure"
}}
</schema>

<context>
University: {university_name}
Seed URL: {seed_url}
</context>

<page_content>
{page_content}
</page_content>"""

PLANNING_RETRY_PROMPT = """Your previous response was not valid JSON. Please try again.

Error: {error}

Respond with ONLY valid JSON matching the schema. No markdown, no explanations."""
