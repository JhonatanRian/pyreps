from __future__ import annotations

import logging
from collections.abc import Generator, Iterable, Iterator, Mapping, Sequence
from operator import itemgetter
from typing import Any

from ..exceptions import ReportError

logger = logging.getLogger("pyreps")


def track_stream[T](
    iterable: Iterable[T], stage: str, exception_cls: type[ReportError]
) -> Generator[T, None, None]:
    """
    Generator that tracks the current row index and enriches exceptions with failure context.
    Uses add_note() (Python 3.11+) to provide detailed failure trace.
    """

    i = -1
    try:
        for i, item in enumerate(iterable):
            yield item
    except Exception as exc:
        # Error from the source iterable (e.g. adapter fetching data)
        # 'i' is the last successful index, so the failure happened at i + 1
        row_number = i + 1
        if isinstance(exc, ReportError):
            if exc.row_number is None:
                exc.row_number = row_number
            exc.add_note(f"failure at row {row_number} during stage: {stage}")
            raise

        new_exc = exception_cls(f"Error during {stage}: {exc}", row_number=row_number)
        new_exc.add_note(f"failure at row {row_number} during stage: {stage}")
        raise new_exc from exc


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


def flatten_record(record: Mapping[str, Any], prefix: str = "") -> Iterator[tuple[str, Any]]:
    """
    Flatten a nested record into an iterator of (dot_notation_key, value).
    """
    for key, value in record.items():
        new_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, Mapping):
            yield from flatten_record(value, new_key)
        else:
            yield new_key, value


def ensure_mapping_stream(
    iterator: Iterator[Any], source_name: str = "Input"
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


def get_cell_value(row: Mapping[str, Any], label: str) -> str:
    """Safely extract a cell value as a string."""
    val = row.get(label)
    return str(val) if val is not None else ""


class WidthTracker:
    """Generator wrapper that tracks max string length per column while streaming rows."""

    __slots__ = ("_rows", "_labels", "max_lens")

    def __init__(
        self,
        rows: Iterable[Mapping[str, Any]],
        labels: Sequence[str],
        exclude_labels: set[str] | None = None,
    ) -> None:
        self._rows = rows
        # Filter labels to only track those that need auto-width.
        exclude = exclude_labels or set()
        self._labels = tuple(label for label in labels if label not in exclude)
        self.max_lens: dict[str, int] = {label: len(label) for label in labels}

    def __iter__(self) -> Iterator[Mapping[str, Any]]:
        labels = self._labels
        if not labels:
            yield from self._rows
            return

        # Optimization: Use enumerate on values to avoid manual indexing overhead
        fetcher = itemgetter(*labels)
        current_max_lens = [self.max_lens[label] for label in labels]

        # Cache localized references to built-ins for performance
        _len, _type, _str, _str_type = len, type, str, str

        for row in self._rows:
            values = fetcher(row)
            if _len(labels) == 1:
                values = (values,)

            for i, val in enumerate(values):
                if val is None:
                    continue

                val_len = _len(val) if _type(val) is _str_type else _len(_str(val))
                if val_len > current_max_lens[i]:
                    current_max_lens[i] = val_len
            yield row

        # Synchronize back to the dictionary
        self.max_lens.update(zip(labels, current_max_lens))
