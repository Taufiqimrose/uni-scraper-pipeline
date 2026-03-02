import re

from bs4 import BeautifulSoup, Comment


class HtmlCleaner:
    """Clean HTML by removing non-content elements for LLM consumption."""

    # Tags that typically contain navigation, not content
    REMOVE_TAGS = {
        "nav", "header", "footer", "aside", "script", "style", "noscript",
        "iframe", "svg", "form", "button", "input", "select", "textarea",
    }

    # CSS classes/IDs that typically indicate non-content
    REMOVE_PATTERNS = re.compile(
        r"(nav|menu|sidebar|footer|header|breadcrumb|cookie|banner|popup|modal|overlay|widget|social|share|comment|advertisement|ad-)",
        re.IGNORECASE,
    )

    def clean(self, html: str) -> str:
        """Clean HTML: remove non-content elements, simplify structure."""
        if not html or not isinstance(html, str):
            return ""
        soup = BeautifulSoup(html, "lxml")

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Remove unwanted tags
        for tag_name in self.REMOVE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Remove elements with navigation-related classes/IDs
        # Copy list to avoid mutation during iteration (decompose can affect tree)
        for element in list(soup.find_all(True)):
            if element is None or not hasattr(element, "get"):
                continue
            try:
                classes = " ".join(element.get("class") or [])
                element_id = element.get("id") or ""
            except (AttributeError, TypeError):
                continue
            if self.REMOVE_PATTERNS.search(classes) or self.REMOVE_PATTERNS.search(element_id):
                element.decompose()

        # Remove empty elements
        for element in list(soup.find_all(True)):
            if element is None or not hasattr(element, "get_text"):
                continue
            if not element.get_text(strip=True) and not element.find_all(["img", "table"]):
                element.decompose()

        # Get the main content area if it exists
        main = soup.find("main") or soup.find(id="content") or soup.find(class_="content")
        if main:
            cleaned = str(main)
        else:
            body = soup.find("body")
            cleaned = str(body) if body else str(soup)

        # Collapse whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)

        return cleaned.strip()

    def extract_text(self, html: str) -> str:
        """Extract plain text from HTML."""
        soup = BeautifulSoup(html, "lxml")
        return soup.get_text(separator="\n", strip=True)

    def extract_links(self, html: str, base_url: str = "") -> list[dict[str, str]]:
        """Extract all links from HTML with their text."""
        soup = BeautifulSoup(html, "lxml")
        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            text = a_tag.get_text(strip=True)
            if text and href and not href.startswith(("#", "javascript:", "mailto:")):
                # Resolve relative URLs
                if base_url and not href.startswith(("http://", "https://")):
                    href = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                links.append({"url": href, "text": text})
        return links
