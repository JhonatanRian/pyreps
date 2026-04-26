from __future__ import annotations

from collections.abc import Iterable
from typing import Any, get_args
from ..exceptions import InvalidSpecError, ReportError


def validate_str(value: Any, field_name: str) -> str:
    """Ensure value is a non-empty string."""
    if not isinstance(value, str) or not value:
        raise InvalidSpecError(
            f"{field_name} must be a non-empty string, got {value!r}"
        )
    return value


def validate_literal(value: Any, literal_type: Any, field_name: str) -> Any:
    """Ensure value is part of a Literal's allowed arguments. Supports PEP 695 aliases."""
    actual_type = getattr(literal_type, "__value__", literal_type)
    allowed = get_args(actual_type)
    if value not in allowed:
        raise InvalidSpecError(f"Invalid {field_name} {value!r}. Allowed: {allowed}")
    return value


def ensure_unique[I](items: Iterable[I], name: str) -> tuple[I, ...]:
    """Ensure all items are unique and return them as a tuple. O(N)."""
    result = tuple(items)
    if len(set(result)) == len(result):
        return result

    seen = set()
    duplicates = {x for x in result if x in seen or seen.add(x)}
    raise InvalidSpecError(f"Duplicate {name} detected: {duplicates}")


def coerce_number(value: Any, *, field_name: str, min_value: float) -> float:
    """Validate and coerce a value to float."""
    if not isinstance(value, (int, float)):
        raise ReportError(f"{field_name} must be a number")
    number = float(value)
    if number < min_value:
        raise ReportError(f"{field_name} must be >= {min_value}")
    return number


def coerce_int(value: Any, *, field_name: str, min_value: int) -> int:
    """Validate and coerce a value to an integer with a minimum threshold."""
    if not isinstance(value, int):
        raise ReportError(f"{field_name} must be an integer")
    if value < min_value:
        raise ReportError(f"{field_name} must be >= {min_value}")
    return value


def coerce_optional_number(
    value: Any, *, field_name: str, min_value: float
) -> float | None:
    """Validate and coerce an optional value to float."""
    if value is None:
        return None
    return coerce_number(value, field_name=field_name, min_value=min_value)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Restrict a value to be within [min_val, max_val]."""
    return max(min_val, min(value, max_val))
