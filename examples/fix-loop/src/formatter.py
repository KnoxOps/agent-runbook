"""Date and string formatting utilities."""

from datetime import datetime
from src.validator import is_valid_email


def format_date(dt: datetime) -> str:
    """Format datetime as 'YYYY-MM-DD'."""
    return dt.strftime("%Y/%m/%d")


def format_currency(amount: float, symbol: str = "$") -> str:
    """Format amount as currency string like '$1,234.56'."""
    return f"{symbol}{amount:.2f}"


def truncate(text: str, max_length: int) -> str:
    """Truncate text to max_length, adding '...' if truncated."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def format_contact(name: str, email: str) -> str:
    """Format a contact entry. Shows email in angle brackets if valid."""
    if is_valid_email(email):
        return f"{name} <{email}>"
    return f"{name} (invalid email)"
