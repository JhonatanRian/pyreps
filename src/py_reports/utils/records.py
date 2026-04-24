from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any


class TupleRecord(Mapping[str, Any]):
    """
    Lightweight Mapping wrapper around a tuple row.
    Avoids creating a new dict for every row by sharing a column-to-index map.
    """

    __slots__ = ("_col_map", "_row")

    def __init__(self, col_map: dict[str, int], row: tuple[Any, ...]) -> None:
        self._col_map = col_map
        self._row = row

    def __getitem__(self, key: str) -> Any:
        # Optimized hot-path: let KeyError bubble up naturally
        return self._row[self._col_map[key]]

    def get(self, key: str, default: Any = None) -> Any:
        """Specialized get to avoid the overhead of generic Mapping.get."""
        try:
            return self._row[self._col_map[key]]
        except KeyError:
            return default

    def __iter__(self) -> Iterator[str]:
        return iter(self._col_map)

    def __len__(self) -> int:
        return len(self._col_map)


def ensure_mapping_stream(
    iterator: Iterator[Any], 
    source_name: str = "Input"
) -> Iterator[Mapping[str, Any]]:
    """
    Optimized wrapper that ensures an iterator yields Mapping objects.
    Uses first-row detection to avoid per-row isinstance checks when possible.
    """
    from ..exceptions import InputAdapterError

    try:
        first = next(iterator)
    except StopIteration:
        return

    if not isinstance(first, Mapping):
        raise InputAdapterError(
            f"{source_name} record must be a mapping, got {type(first).__name__}"
        )

    yield first
    yield from iterator


def wrap_cursor_stream(cursor: Any) -> Iterator[Mapping[str, Any]]:
    """
    Wraps a DB-API cursor into a stream of Mapping objects.
    Optimizes for drivers that already return Mappings.
    """
    iterator = iter(cursor)
    try:
        first = next(iterator)
    except StopIteration:
        return

    if isinstance(first, Mapping):
        yield first
        yield from iterator
    else:
        # Manual zipping for tuple-based rows
        columns = [description[0] for description in cursor.description]
        col_map = {col: i for i, col in enumerate(columns)}
        yield TupleRecord(col_map, first)
        for row in iterator:
            yield TupleRecord(col_map, row)
