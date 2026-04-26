from __future__ import annotations

import itertools
from collections import defaultdict
from typing import Any

from .coercion import BOOL_STRINGS, coerce_value, make_format_cache
from .contracts import ColumnSpec, ColumnType, InputAdapter, OutputFormat, ReportSpec
from .utils.records import flatten_record


def _generate_label(source: str) -> str:
    """Generate a human-friendly label from a source key (e.g., 'user.first_name' -> 'User First Name')."""
    return " ".join(part.replace("_", " ").title() for part in source.split("."))


def _is_strictly_bool(values: list[Any]) -> bool:
    """Check if all values in the sample are strictly boolean-like."""
    for val in values:
        if val is None:
            continue
        if isinstance(val, bool):
            continue
        if isinstance(val, str):
            if val.strip().lower() in BOOL_STRINGS:
                continue
        # We exclude integers (0, 1) to avoid misidentifying IDs as booleans
        return False
    return True


def _detect_type(values: list[Any], source: str) -> ColumnType:
    """Detect the most specific ColumnType that can accommodate all non-null values."""
    non_null_values = [v for v in values if v is not None]
    if not non_null_values:
        return "str"

    cache = make_format_cache()

    # 1. Temporal Detection (datetime > date)
    try:
        is_all_date = True
        for val in non_null_values:
            coerced = coerce_value(val, "datetime", source=source, cache=cache)
            if (
                coerced.hour != 0
                or coerced.minute != 0
                or coerced.second != 0
                or coerced.microsecond != 0
            ):
                is_all_date = False

        if is_all_date:
            try:
                for val in non_null_values:
                    coerce_value(val, "date", source=source, cache=cache)
                return "date"
            except (ValueError, TypeError):
                return "datetime"
        return "datetime"
    except (ValueError, TypeError):
        try:
            for val in non_null_values:
                coerce_value(val, "date", source=source, cache=cache)
            return "date"
        except (ValueError, TypeError):
            pass

    # 2. Boolean Detection (Strict)
    if _is_strictly_bool(non_null_values):
        return "bool"

    # 3. Numeric Detection (int > float)
    try:
        is_all_int = True
        for val in non_null_values:
            if isinstance(val, float) and not val.is_integer():
                is_all_int = False
                break
            coerce_value(val, "int", source=source)
        if is_all_int:
            return "int"
    except (ValueError, TypeError):
        pass

    try:
        for val in non_null_values:
            coerce_value(val, "float", source=source)
        return "float"
    except (ValueError, TypeError):
        pass

    return "str"


def infer_report_spec(
    adapter: InputAdapter[Any],
    data_source: Any,
    sample_size: int = 100,
    output_format: OutputFormat = "csv",
) -> ReportSpec:
    """
    Infer a ReportSpec by sampling the first N records from an InputAdapter.
    Optimized for single-pass performance and minimal memory usage.
    """
    # Use buckets to group values by key in a single pass
    buckets: dict[str, list[Any]] = defaultdict(list)

    # Track the number of records seen
    count = 0
    for record in itertools.islice(adapter.adapt(data_source), sample_size):
        count += 1
        for key, value in flatten_record(record):
            buckets[key].append(value)

    if count == 0:
        raise ValueError("No records found to infer spec from.")

    columns = [
        ColumnSpec(
            label=_generate_label(key),
            source=key,
            type=_detect_type(values, key),
            required=False,
        )
        for key, values in sorted(buckets.items())
    ]

    return ReportSpec(columns=tuple(columns), output_format=output_format)
