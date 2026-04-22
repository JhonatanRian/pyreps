from __future__ import annotations

import functools
from datetime import date, datetime
from typing import Any

from .contracts import ColumnType
from .exceptions import MappingError

_BOOL_TRUTHY = frozenset({"true", "1", "yes", "sim", "on"})
_BOOL_FALSY = frozenset({"false", "0", "no", "não", "nao", "off"})

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y")
_DATETIME_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
)

# State for optimizing date parsing
_LAST_SUCCESSFUL_FORMAT: dict[str, str] = {"date": "", "datetime": ""}


def coerce_value(
    value: Any,
    column_type: ColumnType,
    *,
    source: str,
    record_index: int,
) -> Any:
    """Coerce *value* to the declared *column_type*.

    Returns the coerced value or raises ``MappingError`` on failure.
    ``None`` values pass through without coercion.
    """
    if value is None:
        return None

    try:
        return _COERCERS[column_type](value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise MappingError(
            f"cannot coerce field '{source}' value {value!r} "
            f"to type '{column_type}' in record index {record_index}"
        ) from exc


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


def _coerce_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        
        # Try last successful format first (Performance)
        last_fmt = _LAST_SUCCESSFUL_FORMAT["date"]
        if last_fmt:
            try:
                return datetime.strptime(text, last_fmt).date()
            except ValueError:
                pass

        for fmt in _DATE_FORMATS:
            if fmt == last_fmt:
                continue
            try:
                res = datetime.strptime(text, fmt).date()
                _LAST_SUCCESSFUL_FORMAT["date"] = fmt
                return res
            except ValueError:
                continue
        raise ValueError(f"cannot parse {value!r} as date")
    raise TypeError(f"unsupported type {type(value).__name__} for date coercion")


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        text = value.strip()

        # Try last successful format first (Performance)
        last_fmt = _LAST_SUCCESSFUL_FORMAT["datetime"]
        if last_fmt:
            try:
                return datetime.strptime(text, last_fmt)
            except ValueError:
                pass

        for fmt in _DATETIME_FORMATS:
            if fmt == last_fmt:
                continue
            try:
                res = datetime.strptime(text, fmt)
                _LAST_SUCCESSFUL_FORMAT["datetime"] = fmt
                return res
            except ValueError:
                continue
        raise ValueError(f"cannot parse {value!r} as datetime")
    raise TypeError(f"unsupported type {type(value).__name__} for datetime coercion")


_COERCERS: dict[ColumnType, Any] = {
    "str": _coerce_str,
    "int": _coerce_int,
    "float": _coerce_float,
    "bool": _coerce_bool,
    "date": _coerce_date,
    "datetime": _coerce_datetime,
}
