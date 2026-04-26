from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any, Mapping, NamedTuple

from .coercion import get_coercer_fn, make_format_cache
from .contracts import Record, ReportSpec
from .exceptions import MappingError, CoercionError

_MISSING = object()


class ColumnProcessor(NamedTuple):
    label: str
    parts: tuple[str, ...]
    is_flat: bool
    flat_key: str | None
    required: bool
    default: Any
    coercer_fn: Callable[..., Any] | None
    requires_cache: bool
    column_type: str | None
    formatter: Callable[[Any], Any] | None
    source: str


def map_records(
    records: Iterable[Record], spec: ReportSpec
) -> Iterator[dict[str, Any]]:
    # Localize globals for LOAD_FAST access in the hot loop
    _missing = _MISSING
    _extract = _extract_by_parts
    _mapping_error = MappingError

    cache = make_format_cache()

    # Pre-calculate processors to avoid nested attribute lookups and function calls
    processors: list[ColumnProcessor] = []
    for column in spec.columns:
        coercer_fn = None
        requires_cache = False
        if column.type is not None:
            coercer_fn, requires_cache = get_coercer_fn(
                column.type, column.source, cache
            )

        is_flat = len(column._source_parts) == 1
        processors.append(
            ColumnProcessor(
                label=column.label,
                parts=column._source_parts,
                is_flat=is_flat,
                flat_key=column._source_parts[0] if is_flat else None,
                required=column.required,
                default=column.default,
                coercer_fn=coercer_fn,
                requires_cache=requires_cache,
                column_type=column.type,
                formatter=column.formatter,
                source=column.source,
            )
        )

    for record in records:
        row: dict[str, Any] = {}
        # current_p is used to provide context in the except block
        current_p = processors[0]
        try:
            for p in processors:
                current_p = p
                # Fast-path for flat dictionary keys to bypass function call overhead
                if p.is_flat:
                    value = record.get(p.flat_key, _missing)  # type: ignore[arg-type]
                else:
                    value = _extract(record, p.parts)

                if value is _missing:
                    if p.required:
                        raise _mapping_error(f"required field '{p.source}' missing")
                    value = p.default

                if value is not None:
                    if p.coercer_fn is not None:
                        # Performance: Chamada direta ao coercer sem closure/try-except interno
                        if p.requires_cache:
                            value = p.coercer_fn(value, cache)
                        else:
                            value = p.coercer_fn(value)

                    if p.formatter is not None:
                        value = p.formatter(value)

                row[p.label] = value
            yield row
        except (ValueError, TypeError, OverflowError) as exc:
            # Captura erros de tipo/valor e enriquece com o contexto da coluna atual.
            # O row_number será injetado pelo track_stream no service.py.
            raise CoercionError(
                f"cannot coerce field '{current_p.source}' value {value!r} "
                f"to type '{current_p.column_type}'"
            ) from exc


def _extract_by_parts(record: Mapping[str, Any], parts: tuple[str, ...]) -> Any:
    """Extract a value from a nested mapping using pre-split keys."""
    current: Any = record
    for key in parts:
        if isinstance(current, Mapping) and key in current:
            current = current[key]
        else:
            return _MISSING
    return current
