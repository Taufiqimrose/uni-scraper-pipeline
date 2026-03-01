import pytest

from src.browser.html_cleaner import HtmlCleaner


@pytest.fixture
def cleaner() -> HtmlCleaner:
    return HtmlCleaner()


class TestHtmlCleaner:
    def test_removes_script_tags(self, cleaner: HtmlCleaner) -> None:
        html = "<html><body><p>Content</p><script>alert('x')</script></body></html>"
        result = cleaner.clean(html)
        assert "alert" not in result
        assert "Content" in result

    def test_removes_nav_tags(self, cleaner: HtmlCleaner) -> None:
        html = "<html><body><nav>Menu items</nav><main><p>Main content</p></main></body></html>"
        result = cleaner.clean(html)
        assert "Menu items" not in result
        assert "Main content" in result

    def test_removes_footer(self, cleaner: HtmlCleaner) -> None:
        html = "<html><body><p>Content</p><footer>Footer stuff</footer></body></html>"
        result = cleaner.clean(html)
        assert "Footer stuff" not in result

    def test_removes_navigation_classes(self, cleaner: HtmlCleaner) -> None:
        html = '<html><body><div class="sidebar-nav">Side</div><div class="main-content"><p>Content</p></div></body></html>'
        result = cleaner.clean(html)
        assert "Side" not in result

    def test_preserves_tables(self, cleaner: HtmlCleaner) -> None:
        html = "<html><body><table><tr><td>CSC 130</td><td>3</td></tr></table></body></html>"
        result = cleaner.clean(html)
        assert "CSC 130" in result

    def test_extracts_main_content(self, cleaner: HtmlCleaner) -> None:
        html = "<html><body><div>Before</div><main><p>Main content here</p></main><div>After</div></body></html>"
        result = cleaner.clean(html)
        assert "Main content here" in result

    def test_extract_text(self, cleaner: HtmlCleaner) -> None:
        html = "<html><body><h1>Title</h1><p>Paragraph one</p><p>Paragraph two</p></body></html>"
        text = cleaner.extract_text(html)
        assert "Title" in text
        assert "Paragraph one" in text

    def test_extract_links(self, cleaner: HtmlCleaner) -> None:
        html = '<html><body><a href="/programs/cs">Computer Science</a><a href="#top">Top</a></body></html>'
        links = cleaner.extract_links(html, "https://csus.edu")
        assert len(links) == 1
        assert links[0]["text"] == "Computer Science"
        assert "csus.edu" in links[0]["url"]
