import re
from urllib.parse import urljoin, urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize a URL: add scheme, remove fragments, collapse paths."""
    url = url.strip()

    # Add scheme if missing
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    parsed = urlparse(url)

    # Remove fragment
    parsed = parsed._replace(fragment="")

    # Normalize path: collapse double slashes, remove trailing slash
    path = re.sub(r"/+", "/", parsed.path)
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    parsed = parsed._replace(path=path)

    return urlunparse(parsed)


def extract_domain(url: str) -> str:
    """Extract the domain from a URL (e.g., 'csus.edu' from 'https://catalog.csus.edu/path')."""
    parsed = urlparse(normalize_url(url))
    netloc = parsed.netloc

    # Remove 'www.' prefix
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # Get the base domain (last two parts)
    parts = netloc.split(".")
    if len(parts) > 2:
        return ".".join(parts[-2:])
    return netloc


def make_absolute(base_url: str, relative_url: str) -> str:
    """Convert a relative URL to absolute using a base URL."""
    return urljoin(base_url, relative_url)


def slugify(name: str) -> str:
    """Convert a university name to a URL-safe slug."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs share the same base domain."""
    return extract_domain(url1) == extract_domain(url2)
