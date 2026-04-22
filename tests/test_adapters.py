from __future__ import annotations

import io
import json
import sqlite3

import pytest

from py_reports.adapters import JsonAdapter, JsonStreamingAdapter, ListDictAdapter, SqlAdapter
from py_reports.exceptions import InputAdapterError


def test_list_dict_adapter_normalizes_dict_records() -> None:
    adapter = ListDictAdapter()
    data = [{"id": "1"}, {"id": "2"}]

    result = list(adapter.adapt(data))

    assert result == data


def test_list_dict_adapter_rejects_non_mapping_items() -> None:
    adapter = ListDictAdapter()

    with pytest.raises(InputAdapterError):
        list(adapter.adapt([{"id": "1"}, 2]))


def test_json_adapter_accepts_json_text_array() -> None:
    adapter = JsonAdapter()
    payload = json.dumps([{"id": "1"}, {"id": "2"}])

    result = list(adapter.adapt(payload))

    assert result == [{"id": "1"}, {"id": "2"}]


def test_json_adapter_extracts_items_from_object_payload() -> None:
    adapter = JsonAdapter()
    payload = {"items": [{"id": "1"}, {"id": "2"}]}

    result = list(adapter.adapt(payload))

    assert result == [{"id": "1"}, {"id": "2"}]


def test_json_adapter_wraps_single_object_payload() -> None:
    adapter = JsonAdapter()
    payload = {"id": "1"}

    result = list(adapter.adapt(payload))

    assert result == [{"id": "1"}]


def test_json_adapter_rejects_invalid_payload_type() -> None:
    adapter = JsonAdapter()

    with pytest.raises(InputAdapterError):
        list(adapter.adapt(123))


def _make_sql_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE items (id TEXT PRIMARY KEY, name TEXT, value REAL)")
    conn.executemany(
        "INSERT INTO items VALUES (?, ?, ?)",
        [("1", "Alpha", 10.0), ("2", "Beta", 20.5)],
    )
    conn.commit()
    return conn


def test_sql_adapter_returns_rows_as_dicts() -> None:
    adapter = SqlAdapter(
        query="SELECT id, name, value FROM items ORDER BY id",
        connection=_make_sql_connection(),
    )

    result = list(adapter.adapt(None))

    assert result == [
        {"id": "1", "name": "Alpha", "value": 10.0},
        {"id": "2", "name": "Beta", "value": 20.5},
    ]


def test_sql_adapter_returns_empty_list_for_no_rows() -> None:
    adapter = SqlAdapter(
        query="SELECT id FROM items WHERE id = 'nonexistent'",
        connection=_make_sql_connection(),
    )

    result = list(adapter.adapt(None))

    assert result == []


def test_sql_adapter_raises_for_invalid_sql() -> None:
    conn = sqlite3.connect(":memory:")
    adapter = SqlAdapter(query="SELECT * FROM nonexistent_table", connection=conn)

    with pytest.raises(InputAdapterError):
        list(adapter.adapt(None))


def test_sql_adapter_raises_for_non_select_query() -> None:
    adapter = SqlAdapter(
        query="UPDATE items SET name = 'x'",
        connection=_make_sql_connection(),
    )

    with pytest.raises(InputAdapterError):
        list(adapter.adapt(None))


def test_sql_adapter_works_with_generic_dbapi_connection() -> None:
    """Proves the adapter works with any object that satisfies the DBConnection Protocol."""

    class FakeCursor:
        description = [("id",), ("name",)]

        def __iter__(self):
            return iter([("1", "Alpha"), ("2", "Beta")])

    class FakeConnection:
        def cursor(self):
            c = FakeCursor()
            c.execute = lambda query: None
            return c

    adapter = SqlAdapter(query="SELECT id, name FROM fake", connection=FakeConnection())
    result = list(adapter.adapt(None))
    assert result == [{"id": "1", "name": "Alpha"}, {"id": "2", "name": "Beta"}]


def test_sql_adapter_wraps_generic_driver_errors() -> None:
    """Proves non-sqlite3 exceptions are wrapped as InputAdapterError."""

    class FailConnection:
        def cursor(self):
            raise RuntimeError("connection refused")

    adapter = SqlAdapter(query="SELECT 1", connection=FailConnection())
    with pytest.raises(InputAdapterError, match="connection refused"):
        list(adapter.adapt(None))


def test_json_streaming_adapter_reads_from_path(tmp_path: Path) -> None:
    path = tmp_path / "test.json"
    data = [{"id": "1"}, {"id": "2"}]
    path.write_text(json.dumps(data))

    adapter = JsonStreamingAdapter()
    result = list(adapter.adapt(str(path)))

    assert result == data


def test_json_streaming_adapter_reads_from_binary_stream() -> None:
    data = [{"id": "1"}, {"id": "2"}]
    stream = io.BytesIO(json.dumps(data).encode("utf-8"))

    adapter = JsonStreamingAdapter()
    result = list(adapter.adapt(stream))

    assert result == data


def test_json_streaming_adapter_extracts_nested_path() -> None:
    data = {"records": [{"id": "1"}, {"id": "2"}]}
    stream = io.BytesIO(json.dumps(data).encode("utf-8"))

    adapter = JsonStreamingAdapter(item_path="records.item")
    result = list(adapter.adapt(stream))

    assert result == [{"id": "1"}, {"id": "2"}]


def test_json_streaming_adapter_raises_for_invalid_structure() -> None:
    # Array of primitives instead of mappings
    stream = io.BytesIO(json.dumps([1, 2, 3]).encode("utf-8"))

    adapter = JsonStreamingAdapter()
    with pytest.raises(InputAdapterError, match="Expected mapping record"):
        list(adapter.adapt(stream))


def test_json_streaming_adapter_raises_for_invalid_json() -> None:
    stream = io.BytesIO(b"invalid json")

    adapter = JsonStreamingAdapter()
    with pytest.raises(InputAdapterError, match="JSON streaming parse error"):
        list(adapter.adapt(stream))
