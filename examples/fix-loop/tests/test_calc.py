"""Tests for calculator utilities."""

import pytest
from src import add, subtract, divide, multiply, percentage


class TestBasicOps:
    def test_add(self):
        assert add(2, 3) == 5

    def test_subtract(self):
        assert subtract(5, 3) == 2

    def test_multiply(self):
        assert multiply(3, 4) == 12


class TestDivide:
    def test_basic(self):
        assert divide(10, 2) == 5.0

    def test_divide_by_zero_raises_value_error(self):
        with pytest.raises(ValueError):
            divide(1, 0)


class TestPercentage:
    def test_half(self):
        assert percentage(50, 100) == 50.0

    def test_full(self):
        assert percentage(100, 100) == 100.0

    def test_quarter(self):
        assert percentage(25, 100) == 25.0
