"""Email and input validation utilities."""

import re
from src import percentage


def is_valid_email(email: str) -> bool:
    """Check if email is valid."""
    pattern = r"^[a-zA-Z0-9]+@[a-zA-Z0-9]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def is_positive_integer(value: str) -> bool:
    """Check if string represents a positive integer."""
    try:
        return int(value) >= 0
    except (ValueError, TypeError):
        return False


def sanitize_username(username: str) -> str:
    """Sanitize username: lowercase, strip, max 20 chars."""
    return username.lower().strip()[:20]


def normalize_score(score: float, max_score: float) -> float:
    """Normalize a score to a 0-100 scale."""
    return percentage(score, max_score)
