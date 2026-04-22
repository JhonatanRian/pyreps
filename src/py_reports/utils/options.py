from __future__ import annotations

from typing import Any
from ..exceptions import ReportError

def coerce_number(value: Any, *, field_name: str, min_value: float) -> float:
    """Validate and coerce a value to float."""
    if not isinstance(value, (int, float)):
        raise ReportError(f"{field_name} must be a number")
    number = float(value)
    if number < min_value:
        raise ReportError(f"{field_name} must be >= {min_value}")
    return number

def coerce_optional_number(
    value: Any, *, field_name: str, min_value: float
) -> float | None:
    """Validate and coerce an optional value to float."""
    if value is None:
        return None
    return coerce_number(value, field_name=field_name, min_value=min_value)
