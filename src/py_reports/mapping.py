from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any, Mapping

from .coercion import coerce_value, make_format_cache
from .contracts import Record, ReportSpec
from .exceptions import MappingError


_MISSING = object()


def map_records(
    records: Iterable[Record], spec: ReportSpec
) -> Iterator[dict[str, Any]]:
    cache = make_format_cache()
    for index, record in enumerate(records):
        row: dict[str, Any] = {}
        for column in spec.columns:
            value = _extract_by_path(record, column.source)
            if value is _MISSING:
                if column.required:
                    raise MappingError(
                        f"required field '{column.source}' missing in record index {index}"
                    )
                value = column.default

            if column.type is not None and value is not None:
                value = coerce_value(
                    value, column.type, source=column.source,
                    record_index=index, cache=cache,
                )

            if column.formatter is not None and value is not None:
                value = column.formatter(value)

            row[column.label] = value
        yield row


def _extract_by_path(record: Mapping[str, Any], path: str) -> Any:
    """Extract a value from a nested mapping using dot notation."""
    current: Any = record
    for key in path.split("."):
        if isinstance(current, Mapping) and key in current:
            current = current[key]
        else:
            return _MISSING
    return current
