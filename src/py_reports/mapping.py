from __future__ import annotations

from typing import Any, Mapping

from .coercion import coerce_value
from .contracts import Record, ReportSpec
from .exceptions import MappingError


_MISSING = object()


def map_records(records: list[Record], spec: ReportSpec) -> list[dict[str, Any]]:
    mapped_rows: list[dict[str, Any]] = []
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
                    value, column.type, source=column.source, record_index=index
                )

            if column.formatter is not None and value is not None:
                value = column.formatter(value)

            row[column.label] = value
        mapped_rows.append(row)
    return mapped_rows


def _extract_by_path(record: Mapping[str, Any], path: str) -> Any:
    current: Any = record
    for key in path.split("."):
        if isinstance(current, Mapping) and key in current:
            current = current[key]
            continue
        return _MISSING
    return current
