# Fix Loop Report

## Summary

All 33 tests passing after 3 iterations. Started with 16 failures across 3 test files.

## Iterations

### Iteration 1: `src/__init__.py`

- **`percentage()`**: multiplied by 10 instead of 100
- **`divide()`**: raised `ZeroDivisionError` instead of `ValueError`

Resolved 6 failures (4 in test_calc.py, 2 in test_validator.py via `normalize_score`).

### Iteration 2: `src/validator.py`

- **`is_valid_email()`**: regex rejected dots, underscores, and hyphens in local part
- **`is_positive_integer()`**: treated 0 as positive (`>= 0` instead of `> 0`)

Resolved 5 failures (4 in test_validator.py, 1 in test_formatter.py via `format_contact`).

### Iteration 3: `src/formatter.py`

- **`format_date()`**: used `/` separator instead of `-`
- **`format_currency()`**: missing thousand separators (`,`)
- **`truncate()`**: didn't account for ellipsis length in max_length

Resolved 5 failures.

## Cascading Dependencies

The design demonstrates how fixing root dependencies clears downstream failures:

1. Fixing `percentage()` in `__init__.py` automatically fixed `normalize_score()` in validator.py (which delegates to it)
2. Fixing `is_valid_email()` in validator.py automatically fixed `format_contact()` in formatter.py (which calls it for validation)

## Final Results

```
33 passed in 0.03s
```
