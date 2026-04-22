from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from typing import Any

import ijson
import orjson
from pathlib import Path

from .contracts import DBConnection, InputAdapter, Record
from .exceptions import InputAdapterError


class ListDictAdapter(InputAdapter):
    def adapt(self, data_source: Any) -> Iterable[Record]:
        if not isinstance(data_source, Iterable):
            raise InputAdapterError("list/dict adapter requires an iterable source")

        for item in data_source:
            if not isinstance(item, Mapping):
                raise InputAdapterError("all records must be mappings (dict-like)")
            yield item


class JsonAdapter(InputAdapter):
    """
    Adapter for JSON data already present in memory.
    Supports JSON strings, bytes, or pre-parsed dicts/lists.
    For large files, use JsonStreamingAdapter instead.
    """

    def adapt(self, data_source: Any) -> Iterable[Record]:
        if isinstance(data_source, (str, bytes, bytearray)):
            payload = orjson.loads(data_source)
        elif isinstance(data_source, Mapping) or isinstance(data_source, list):
            payload = data_source
        else:
            raise InputAdapterError(
                "json adapter expects JSON text, dict, or list payload"
            )

        if isinstance(payload, Mapping):
            if "items" in payload and isinstance(payload["items"], list):
                payload = payload["items"]
            else:
                payload = [payload]

        if not isinstance(payload, list):
            raise InputAdapterError("json payload must resolve to a list of records")

        for item in payload:
            if not isinstance(item, Mapping):
                raise InputAdapterError("json record entries must be mapping objects")
            yield item


class JsonStreamingAdapter(InputAdapter):
    """
    Adapter for high-performance JSON streaming from files or binary streams.
    Uses ijson to parse the input iteratively, keeping memory usage constant.
    """

    def __init__(self, item_path: str = "item") -> None:
        """
        Args:
            item_path: ijson path to the records.
                       Use "item" for a root-level array [{}, {}].
                       Use "some_key.item" for a nested array {"some_key": [{}, {}]}.
        """
        self.item_path = item_path

    def adapt(self, data_source: Any) -> Iterable[Record]:
        if isinstance(data_source, (str, Path)):
            with open(data_source, "rb") as f:
                yield from self._iterate(f)
        elif hasattr(data_source, "read"):
            yield from self._iterate(data_source)
        else:
            raise InputAdapterError(
                "JsonStreamingAdapter expects a file path (str/Path) or a binary file-like object"
            )

    def _iterate(self, stream: Any) -> Iterable[Record]:
        try:
            for item in ijson.items(stream, self.item_path):
                if not isinstance(item, Mapping):
                    raise InputAdapterError(
                        f"Expected mapping record at '{self.item_path}', got {type(item).__name__}"
                    )
                yield item
        except ijson.JSONError as exc:
            raise InputAdapterError(f"JSON streaming parse error: {exc}") from exc


class SqlAdapter(InputAdapter):
    def __init__(self, *, query: str, connection: DBConnection) -> None:
        self._query = query
        self._connection = connection

    def adapt(self, data_source: Any) -> Iterable[Record]:
        try:
            cursor = self._connection.cursor()
            cursor.execute(self._query)
        except Exception as exc:
            raise InputAdapterError(f"SQL query failed: {exc}") from exc

        if cursor.description is None:
            raise InputAdapterError(
                "SQL query did not return rows; only SELECT statements are supported"
            )

        columns = [description[0] for description in cursor.description]
        for row in cursor:
            yield dict(zip(columns, row))

