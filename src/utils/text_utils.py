import re


def clean_whitespace(text: str) -> str:
    """Normalize whitespace in a string."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_course_code(text: str) -> str | None:
    """Extract a course code from text (e.g., 'CSC 130', 'MATH 26A')."""
    match = re.search(r"([A-Z]{2,5})\s*(\d{1,4}[A-Z]?)", text)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return None


def extract_units(text: str) -> int | None:
    """Extract unit count from text like '3 units' or '(4)'."""
    match = re.search(r"(\d+)\s*(?:units?|credits?|hrs?|hours?)", text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Try parenthesized number
    match = re.search(r"\((\d+)\)", text)
    if match:
        return int(match.group(1))

    return None


def deduplicate_preserving_order(items: list[str]) -> list[str]:
    """Remove duplicates from a list while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip().lower()
        if normalized not in seen:
            seen.add(normalized)
            result.append(item.strip())
    return result


def truncate_for_llm(text: str, max_chars: int = 100_000) -> str:
    """Truncate text to fit within LLM context limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... content truncated for length ...]"
