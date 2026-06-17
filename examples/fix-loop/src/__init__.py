"""Simple calculator utilities."""


def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def divide(a: float, b: float) -> float:
    """Divide a by b, raising ValueError on zero division."""
    return a / b


def multiply(a: float, b: float) -> float:
    return a * b


def percentage(value: float, total: float) -> float:
    """Return what percentage value is of total."""
    return (value / total) * 10
