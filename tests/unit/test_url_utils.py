import pytest

from src.utils.url_utils import extract_domain, is_same_domain, make_absolute, normalize_url, slugify


class TestNormalizeUrl:
    def test_adds_https_scheme(self) -> None:
        assert normalize_url("csus.edu") == "https://csus.edu"

    def test_preserves_existing_https(self) -> None:
        assert normalize_url("https://csus.edu") == "https://csus.edu"

    def test_removes_fragment(self) -> None:
        assert normalize_url("https://csus.edu/page#section") == "https://csus.edu/page"

    def test_collapses_double_slashes(self) -> None:
        assert normalize_url("https://csus.edu//catalog//page") == "https://csus.edu/catalog/page"

    def test_removes_trailing_slash(self) -> None:
        assert normalize_url("https://csus.edu/catalog/") == "https://csus.edu/catalog"

    def test_keeps_root_slash(self) -> None:
        result = normalize_url("https://csus.edu/")
        assert result == "https://csus.edu/"


class TestExtractDomain:
    def test_simple_domain(self) -> None:
        assert extract_domain("https://csus.edu/catalog") == "csus.edu"

    def test_subdomain(self) -> None:
        assert extract_domain("https://catalog.csus.edu/programs") == "csus.edu"

    def test_www_prefix(self) -> None:
        assert extract_domain("https://www.csus.edu") == "csus.edu"


class TestMakeAbsolute:
    def test_relative_path(self) -> None:
        assert make_absolute("https://csus.edu/catalog", "/programs") == "https://csus.edu/programs"

    def test_already_absolute(self) -> None:
        assert make_absolute("https://csus.edu", "https://other.edu/page") == "https://other.edu/page"


class TestSlugify:
    def test_simple_name(self) -> None:
        assert slugify("Sacramento State") == "sacramento-state"

    def test_with_special_chars(self) -> None:
        assert slugify("UC Berkeley (Cal)") == "uc-berkeley-cal"

    def test_with_commas(self) -> None:
        assert slugify("California State University, Sacramento") == "california-state-university-sacramento"


class TestIsSameDomain:
    def test_same_domain(self) -> None:
        assert is_same_domain("https://catalog.csus.edu", "https://www.csus.edu") is True

    def test_different_domains(self) -> None:
        assert is_same_domain("https://csus.edu", "https://mit.edu") is False
