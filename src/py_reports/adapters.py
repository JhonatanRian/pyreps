from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping
from typing import Any

from .contracts import InputAdapter, Record
from .exceptions import InputAdapterError


class ListDictAdapter(InputAdapter):
    def adapt(self, data_source: Any) -> Iterable[Record]:
        if not isinstance(data_source, Iterable):
            raise InputAdapterError("list/dict adapter requires an iterable source")

        normalized: list[Record] = []
        for item in data_source:
            if not isinstance(item, Mapping):
                raise InputAdapterError("all records must be mappings (dict-like)")
            normalized.append(item)
        return normalized


class JsonAdapter(InputAdapter):
    def adapt(self, data_source: Any) -> Iterable[Record]:
        if isinstance(data_source, (str, bytes, bytearray)):
            payload = json.loads(data_source)
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

        normalized: list[Record] = []
        for item in payload:
            if not isinstance(item, Mapping):
                raise InputAdapterError("json record entries must be mapping objects")
            normalized.append(item)
        return normalized


class SqlAdapter(InputAdapter):
    def __init__(self, *, query: str, connection: sqlite3.Connection) -> None:
        self._query = query
        self._connection = connection

    def adapt(self, data_source: Any) -> Iterable[Record]:
        try:
            cursor = self._connection.execute(self._query)
        except sqlite3.Error as exc:
            raise InputAdapterError(f"SQL query failed: {exc}") from exc

        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
