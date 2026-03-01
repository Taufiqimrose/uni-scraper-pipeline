import pytest

from src.utils.text_utils import (
    clean_whitespace,
    deduplicate_preserving_order,
    extract_course_code,
    extract_units,
    truncate_for_llm,
)


class TestCleanWhitespace:
    def test_collapses_spaces(self) -> None:
        assert clean_whitespace("hello    world") == "hello world"

    def test_collapses_newlines(self) -> None:
        assert clean_whitespace("a\n\n\n\nb") == "a\n\nb"

    def test_strips(self) -> None:
        assert clean_whitespace("  hello  ") == "hello"


class TestExtractCourseCode:
    def test_standard_code(self) -> None:
        assert extract_course_code("Take CSC 130 next semester") == "CSC 130"

    def test_code_with_letter(self) -> None:
        assert extract_course_code("MATH 26A is required") == "MATH 26A"

    def test_no_code(self) -> None:
        assert extract_course_code("No course here") is None


class TestExtractUnits:
    def test_units_keyword(self) -> None:
        assert extract_units("3 units") == 3

    def test_credits_keyword(self) -> None:
        assert extract_units("4 credits") == 4

    def test_parenthesized(self) -> None:
        assert extract_units("CSC 130 (3)") == 3

    def test_no_units(self) -> None:
        assert extract_units("No unit info") is None


class TestDeduplicatePreservingOrder:
    def test_removes_duplicates(self) -> None:
        result = deduplicate_preserving_order(["a", "b", "a", "c", "b"])
        assert result == ["a", "b", "c"]

    def test_case_insensitive(self) -> None:
        result = deduplicate_preserving_order(["CSC 130", "csc 130", "CSC 131"])
        assert len(result) == 2


class TestTruncateForLlm:
    def test_short_text_unchanged(self) -> None:
        text = "short"
        assert truncate_for_llm(text) == text

    def test_long_text_truncated(self) -> None:
        text = "x" * 200
        result = truncate_for_llm(text, max_chars=100)
        assert len(result) < 200
        assert "truncated" in result
