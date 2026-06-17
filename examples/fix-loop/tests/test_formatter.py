"""Tests for formatter module."""

from datetime import datetime
from src.formatter import format_date, format_currency, truncate, format_contact


class TestFormatDate:
    def test_basic_format(self):
        dt = datetime(2024, 3, 15)
        assert format_date(dt) == "2024-03-15"

    def test_single_digit_month_day(self):
        dt = datetime(2024, 1, 5)
        assert format_date(dt) == "2024-01-05"


class TestFormatCurrency:
    def test_basic_format(self):
        assert format_currency(1234.5) == "$1,234.50"

    def test_large_number(self):
        assert format_currency(1000000) == "$1,000,000.00"

    def test_custom_symbol(self):
        assert format_currency(99.9, "€") == "€99.90"


class TestTruncate:
    def test_short_text_unchanged(self):
        assert truncate("hello", 10) == "hello"

    def test_long_text_truncated(self):
        result = truncate("hello world", 8)
        assert result == "hello..."
        assert len(result) <= 8

    def test_exact_length(self):
        assert truncate("hello", 5) == "hello"


class TestFormatContact:
    def test_valid_email(self):
        assert format_contact("Alice", "alice@example.com") == "Alice <alice@example.com>"

    def test_email_with_dots(self):
        assert format_contact("Bob", "bob.smith@example.com") == "Bob <bob.smith@example.com>"

    def test_invalid_email(self):
        assert format_contact("Eve", "not-an-email") == "Eve (invalid email)"
