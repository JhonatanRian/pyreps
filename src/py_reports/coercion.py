from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from .contracts import ColumnType
from .exceptions import CoercionError

_BOOL_TRUTHY = frozenset({"true", "1", "yes", "sim", "on"})
_BOOL_FALSY = frozenset({"false", "0", "no", "não", "nao", "off"})

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
    record_index: int,
    cache: FormatCache | None = None,
) -> Any:
    """Coerce *value* to the declared *column_type*.

    Returns the coerced value or raises ``CoercionError`` on failure.
    ``None`` values pass through without coercion.
    """
    if value is None:
        return None

    # Reuse the specialized coercer closure to avoid logic duplication
    coercer_fn = get_coercer_fn(column_type, source, cache or make_format_cache())
    return coercer_fn(value, record_index)


def get_coercer_fn(
    column_type: ColumnType,
    source: str,
    cache: FormatCache,
) -> Callable[[Any, int], Any]:
    """Create a pre-bound coercer closure for the given column type and source."""
    coercer = _COERCERS[column_type]
    requires_cache = column_type in _CACHED_TYPES

    def coerce_fn(value: Any, record_index: int) -> Any:
        try:
            if requires_cache:
                return coercer(value, cache)
            return coercer(value)
        except (ValueError, TypeError, OverflowError) as exc:
            raise CoercionError(
                f"cannot coerce field '{source}' value {value!r} "
                f"to type '{column_type}' in record index {record_index}"
            ) from exc

    return coerce_fn


def _coerce_str(value: Any) -> str:
    return str(value)


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (float, int)):
        if value != int(value):
            raise ValueError(f"cannot losslessly convert {value!r} to int")
        return int(value)
    if isinstance(value, str):
        return int(value.strip())
    return int(value)


def _coerce_float(value: Any) -> float:
    if isinstance(value, str):
        return float(value.strip())
    return float(value)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _BOOL_TRUTHY:
            return True
        if normalized in _BOOL_FALSY:
            return False
        raise ValueError(f"cannot interpret {value!r} as bool")
    raise TypeError(f"unsupported type {type(value).__name__} for bool coercion")


def _parse_with_cache(
    text: str,
    formats: tuple[str, ...],
    cache_key: str,
    cache: FormatCache | None,
) -> datetime:
    """Try cached format first, then brute-force all formats. Returns raw datetime."""
    last_fmt = cache.get(cache_key, "") if cache else ""
    if last_fmt:
        try:
            return datetime.strptime(text, last_fmt)
        except ValueError:
            pass

    for fmt in formats:
        if fmt == last_fmt:
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
