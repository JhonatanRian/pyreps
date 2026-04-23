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

    def __iter__(self) -> Iterator[str]:
        return iter(self._col_map)

    def __len__(self) -> int:
        return len(self._col_map)
