from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from .contracts import ColumnType

_BOOL_TRUTHY = frozenset({"true", "1", "yes", "sim", "on"})
_BOOL_FALSY = frozenset({"false", "0", "no", "não", "nao", "off"})

BOOL_STRINGS = _BOOL_TRUTHY | _BOOL_FALSY
"""Set of all strings interpreted as booleans."""

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y")
_DATETIME_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
)

FormatCache = dict[str, str]
"""Per-call cache that stores the last successful date/datetime parse format.

Scoped to a single ``map_records()`` invocation so that concurrent calls
(threads or async tasks) never share mutable state.
"""

_CACHED_TYPES = frozenset({"date", "datetime"})


def make_format_cache() -> FormatCache:
    """Create a new format cache scoped to a single mapping run."""
    return {"date": "", "datetime": ""}


def coerce_value(
    value: Any,
    column_type: ColumnType,
    *,
    source: str,
    cache: FormatCache | None = None,
) -> Any:
    """Coerce *value* to the declared *column_type*.

    Returns the coerced value or raises ``CoercionError`` on failure.
    ``None`` values pass through without coercion.
    """
    if value is None:
        return None

    # Reuse the specialized coercer closure to avoid logic duplication
    local_cache = cache or make_format_cache()
    coercer, requires_cache = get_coercer_fn(column_type, source, local_cache)
    return coercer(value, local_cache) if requires_cache else coercer(value)


def get_coercer_fn(
    column_type: ColumnType,
    source: str,
    cache: FormatCache,
) -> tuple[Callable[..., Any], bool]:
    """
    Returns a (coercer_fn, requires_cache) tuple.
    The coercer_fn is naked (no try/except) to minimize hot-path overhead.
    """
    coercer = _COERCERS[column_type]
    requires_cache = column_type in _CACHED_TYPES
    return coercer, requires_cache


def _coerce_str(value: Any) -> str:
    return str(value)


def _coerce_int(value: Any) -> int:
    v_type = type(value)
    if v_type is int:
        return value
    if v_type is float:
        if value % 1 == 0:
            return int(value)
        raise ValueError(f"cannot losslessly convert {value!r} to int")
    if v_type is str:
        return int(value)
    if v_type is bool:
        return int(value)
    return int(value)


def _coerce_float(value: Any) -> float:
    v_type = type(value)
    if v_type is float:
        return value
    if v_type is int:
        return float(value)
    if v_type is str:
        return float(value)
    return float(value)


def _coerce_bool(value: Any) -> bool:
    v_type = type(value)
    if v_type is bool:
        return value
    if v_type is int or v_type is float:
        return bool(value)
    if v_type is str:
        # Fast-path for common exact matches to avoid strip().lower()
        if value == "1" or value == "true":
            return True
        if value == "0" or value == "false":
            return False

        normalized = value.strip().lower()
        if normalized in _BOOL_TRUTHY:
            return True
        if normalized in _BOOL_FALSY:
            return False
        raise ValueError(f"cannot interpret {value!r} as bool")
    raise TypeError(f"unsupported type {v_type.__name__} for bool coercion")


def _parse_with_cache(
    text: str,
    formats: tuple[str, ...],
    cache_key: str,
    cache: FormatCache | None,
) -> datetime:
    """Try cached format first, then structural validation, then brute-force."""
    if not text:
        raise ValueError("empty string")

    # Fast path: ISO-like (YYYY-MM-DD...)
    # Handles: %Y-%m-%d, %Y-%m-%dT%H:%M:%S, %Y-%m-%d %H:%M:%S
    # fromisoformat is ~40x faster than strptime and handles 'T' or ' ' separators.
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass

    last_fmt = cache.get(cache_key, "") if cache else ""
    if last_fmt:
        # Structural check for cached format to avoid expensive ValueError
        if ("/" in last_fmt and "/" in text) or ("-" in last_fmt and "-" in text):
            try:
                return datetime.strptime(text, last_fmt)
            except ValueError:
                pass

    for fmt in formats:
        if fmt == last_fmt:
            continue

        # Structural validation to avoid expensive strptime call when it will surely fail.
        # Exceptions are zero-cost in 3.11+ ONLY if not raised.
        if "/" in fmt:
            if "/" not in text:
                continue
        elif "-" in fmt:
            if "-" not in text:
                continue

        try:
            result = datetime.strptime(text, fmt)
            if cache is not None:
                cache[cache_key] = fmt
            return result
        except ValueError:
            continue

    raise ValueError(f"cannot parse {text!r}")


def _coerce_temporal(
    value: Any,
    formats: tuple[str, ...],
    cache_key: str,
    cache: FormatCache | None,
) -> datetime:
    """Consolidated logic for date/datetime coercion."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        return _parse_with_cache(value.strip(), formats, cache_key, cache)
    raise TypeError(f"unsupported type {type(value).__name__} for {cache_key} coercion")


def _coerce_date(value: Any, cache: FormatCache | None = None) -> date:
    return _coerce_temporal(value, _DATE_FORMATS, "date", cache).date()


def _coerce_datetime(value: Any, cache: FormatCache | None = None) -> datetime:
    return _coerce_temporal(value, _DATETIME_FORMATS, "datetime", cache)


_COERCERS: dict[ColumnType, Any] = {
    "str": _coerce_str,
    "int": _coerce_int,
    "float": _coerce_float,
    "bool": _coerce_bool,
    "date": _coerce_date,
    "datetime": _coerce_datetime,
}
