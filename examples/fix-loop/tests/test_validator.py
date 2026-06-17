"""Tests for validator module."""

from src.validator import (
    is_valid_email,
    is_positive_integer,
    sanitize_username,
    normalize_score,
)


class TestIsValidEmail:
    def test_simple_email(self):
        assert is_valid_email("user@example.com") is True

    def test_email_with_dots(self):
        assert is_valid_email("first.last@example.com") is True

    def test_email_with_underscore(self):
        assert is_valid_email("user_name@example.com") is True

    def test_email_with_hyphen(self):
        assert is_valid_email("user-name@example.com") is True

    def test_invalid_no_at(self):
        assert is_valid_email("userexample.com") is False


class TestIsPositiveInteger:
    def test_positive(self):
        assert is_positive_integer("5") is True

    def test_zero_is_not_positive(self):
        assert is_positive_integer("0") is False

    def test_negative(self):
        assert is_positive_integer("-3") is False

    def test_non_numeric(self):
        assert is_positive_integer("abc") is False


class TestSanitizeUsername:
    def test_basic(self):
        assert sanitize_username("  Hello  ") == "hello"

    def test_long_name_truncated(self):
        assert len(sanitize_username("a" * 30)) == 20


class TestNormalizeScore:
    def test_half_score(self):
        assert normalize_score(50, 200) == 25.0

    def test_full_score(self):
        assert normalize_score(100, 100) == 100.0

    def test_zero_score(self):
        assert normalize_score(0, 100) == 0.0
