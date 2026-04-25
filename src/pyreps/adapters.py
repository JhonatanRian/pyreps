from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, override

import ijson
import orjson

from .contracts import DBConnection, InputAdapter, Record
from .exceptions import InputAdapterError
from .utils.db import get_cursor
from .utils.records import ensure_mapping_stream, wrap_cursor_stream


class ListDictAdapter(InputAdapter[Iterable[Mapping[str, Any]]]):
    """Adapter for data already in memory as an iterable of dicts."""

    @override
    def adapt(self, data_source: Iterable[Mapping[str, Any]]) -> Iterable[Record]:
        match data_source:
            case str() | bytes() | bytearray():
                raise InputAdapterError("list/dict adapter requires an iterable of mappings")
            case Iterable():
                return ensure_mapping_stream(iter(data_source))
            case _:
                raise InputAdapterError("list/dict adapter requires an iterable of mappings")


class JsonAdapter(InputAdapter[str | bytes | Mapping[str, Any] | list[Any]]):
    """
    Adapter for JSON data already present in memory.
    Supports JSON strings, bytes, or pre-parsed dicts/lists.
    """

    @override
    def adapt(self, data_source: Any) -> Iterable[Record]:
        match data_source:
            case str() | bytes() | bytearray():
                try:
                    payload = orjson.loads(data_source)
                except Exception as exc:
                    raise InputAdapterError(f"Failed to parse JSON: {exc}") from exc
            case Mapping() | list():
                payload = data_source
            case _:
                raise InputAdapterError("json adapter expects JSON text, dict, or list payload")

        if isinstance(payload, Mapping):
            items = payload.get("items")
            payload = items if isinstance(items, list) else [payload]

        if not isinstance(payload, list):
            raise InputAdapterError("json payload must resolve to a list of records")

        return ensure_mapping_stream(iter(payload))


@dataclass(slots=True, frozen=True)
class JsonStreamingAdapter(InputAdapter[str | Path | BinaryIO]):
    """
    Adapter for high-performance JSON streaming from files or binary streams.
    Uses ijson to parse the input iteratively, keeping memory usage constant.
    """

    item_path: str = "item"

    @override
    def adapt(self, data_source: str | Path | BinaryIO) -> Iterable[Record]:
        match data_source:
            case str() | Path():
                try:
                    with open(data_source, "rb") as f:
                        yield from self._iterate(f)
                except Exception as exc:
                    raise InputAdapterError(f"Streaming JSON failed: {exc}") from exc
            case stream if hasattr(stream, "read"):
                yield from self._iterate(stream)
            case _:
                raise InputAdapterError(
                    "JsonStreamingAdapter expects a file path (str/Path) or a binary file-like object"
                )

    def _iterate(self, stream: BinaryIO) -> Iterator[Record]:
        try:
            yield from ensure_mapping_stream(ijson.items(stream, self.item_path))
        except ijson.JSONError as exc:
            raise InputAdapterError(f"JSON streaming parse error: {exc}") from exc


@dataclass(slots=True, frozen=True)
class SqlAdapter(InputAdapter[None]):
    """Adapter for SQL query results via a DB-API 2.0 connection."""

    query: str
    connection: DBConnection
    params: tuple[Any, ...] | dict[str, Any] | None = None

    @override
    def adapt(self, data_source: None = None) -> Iterable[Record]:
        from contextlib import closing

        with closing(get_cursor(self.connection)) as cursor:
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

            yield from wrap_cursor_stream(cursor)
