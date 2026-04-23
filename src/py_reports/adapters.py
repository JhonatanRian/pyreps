from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

import ijson
import orjson

from .contracts import DBConnection, InputAdapter, Record
from .exceptions import InputAdapterError
from .utils.records import TupleRecord


def _validate_mappings(records: Iterable[Any]) -> Iterator[Record]:
    """Helper generator to validate that each record is a Mapping."""
    for item in records:
        if not isinstance(item, Mapping):
            raise InputAdapterError(
                f"Input record must be a mapping, got {type(item).__name__}"
            )
        yield item


class ListDictAdapter(InputAdapter):
    """Adapter for data already in memory as an iterable of dicts."""

    def adapt(self, data_source: Any) -> Iterable[Record]:
        if not isinstance(data_source, Iterable) or isinstance(
            data_source, (str, bytes, bytearray)
        ):
            raise InputAdapterError("list/dict adapter requires an iterable of mappings")

        return _validate_mappings(data_source)


class JsonAdapter(InputAdapter):
    """
    Adapter for JSON data already present in memory.
    Supports JSON strings, bytes, or pre-parsed dicts/lists.
    If the top-level object has an "items" key containing a list, it will be used as the record source.
    For large files, use JsonStreamingAdapter instead.
    """

    def adapt(self, data_source: Any) -> Iterable[Record]:
        if isinstance(data_source, (str, bytes, bytearray)):
            try:
                payload = orjson.loads(data_source)
            except Exception as exc:
                raise InputAdapterError(f"Failed to parse JSON: {exc}") from exc
        elif isinstance(data_source, (Mapping, list)):
            payload = data_source
        else:
            raise InputAdapterError(
                "json adapter expects JSON text, dict, or list payload"
            )

        if isinstance(payload, Mapping):
            items = payload.get("items")
            payload = items if isinstance(items, list) else [payload]

        if not isinstance(payload, list):
            raise InputAdapterError("json payload must resolve to a list of records")

        return _validate_mappings(payload)


@dataclass(slots=True, frozen=True)
class JsonStreamingAdapter(InputAdapter):
    """
    Adapter for high-performance JSON streaming from files or binary streams.
    Uses ijson to parse the input iteratively, keeping memory usage constant.
    """

    item_path: str = "item"

    def adapt(self, data_source: Any) -> Iterable[Record]:
        if isinstance(data_source, (str, Path)):
            try:
                with open(data_source, "rb") as f:
                    yield from self._iterate(f)
            except Exception as exc:
                raise InputAdapterError(f"Streaming JSON failed: {exc}") from exc
        elif hasattr(data_source, "read"):
            yield from self._iterate(data_source)
        else:
            raise InputAdapterError(
                "JsonStreamingAdapter expects a file path (str/Path) or a binary file-like object"
            )

    def _iterate(self, stream: BinaryIO) -> Iterator[Record]:
        try:
            yield from _validate_mappings(ijson.items(stream, self.item_path))
        except ijson.JSONError as exc:
            raise InputAdapterError(f"JSON streaming parse error: {exc}") from exc


def _is_closed_connection_error(exc: Exception) -> bool:
    """Classify if an exception indicates a closed or invalid database connection."""
    error_type = type(exc).__name__.lower()
    if error_type in ("programmingerror", "interfaceerror", "operationalerror"):
        return True
    return "closed" in str(exc).lower()


@dataclass(slots=True, frozen=True)
class SqlAdapter(InputAdapter):
    """Adapter for SQL query results via a DB-API 2.0 connection."""

    query: str
    connection: DBConnection
    params: tuple[Any, ...] | dict[str, Any] | None = None

    def adapt(self, data_source: Any) -> Iterable[Record]:
        # Proactive check for drivers that support the 'closed' attribute (e.g., psycopg2)
        is_closed = getattr(self.connection, "closed", False)
        if callable(is_closed):
            is_closed = is_closed()
        if is_closed:
            raise InputAdapterError("The connection is closed.")

        try:
            cursor = self.connection.cursor()
        except Exception as exc:
            if _is_closed_connection_error(exc):
                raise InputAdapterError(
                    f"Failed to create cursor. The connection might be closed or invalid. Original error: {exc}"
                ) from exc
            raise InputAdapterError(f"SQL cursor creation failed: {exc}") from exc

        try:
            try:
                if self.params is not None:
                    cursor.execute(self.query, self.params)
                else:
                    cursor.execute(self.query)
            except Exception as exc:
                raise InputAdapterError(f"SQL query failed: {exc}") from exc

            if cursor.description is None:
                raise InputAdapterError(
                    "SQL query did not return rows; only SELECT statements are supported"
                )

            # Hot-path optimization: detect if the driver returns mappings natively (e.g. DictCursor)
            # and avoid the cost of manual TupleRecord zipping and type-checking in the loop.
            iterator = iter(cursor)
            try:
                first_row = next(iterator)
            except StopIteration:
                return

            if isinstance(first_row, Mapping):
                yield first_row
                yield from iterator
            else:
                # Manual zipping for tuple-based rows
                columns = [description[0] for description in cursor.description]
                col_map = {col: i for i, col in enumerate(columns)}
                yield TupleRecord(col_map, first_row)
                for row in iterator:
                    yield TupleRecord(col_map, row)
        finally:
            cursor.close()
