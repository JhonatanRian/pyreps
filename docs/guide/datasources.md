# Data Sources

**{{ project_name }}** accepts data from multiple sources via adapters. Detection is automatic for the most common types.

## list[dict] — ListDictAdapter

The most direct way. Accepts any iterable of dicts:

```python
data = [
    {"id": 1, "name": "Ana"},
    {"id": 2, "name": "Bruno"},
]

generate_report(data_source=data, spec=spec, destination="out.csv")
```

!!! tip "Generators"
    Accepts generators and lazy iterables — perfect for processing data on demand:

    ```python
    def fetch_records():
        for page in api.paginate():
            yield from page["items"]

    generate_report(data_source=fetch_records(), spec=spec, destination="out.csv")
    ```

## JSON — JsonAdapter

Accepts JSON strings, bytes, dicts, and lists. Parsing via **orjson** (Rust, ~6x faster than stdlib).

=== "JSON String"

    ```python
    payload = '[{"id": 1, "name": "Ana"}, {"id": 2, "name": "Bruno"}]'
    generate_report(data_source=payload, spec=spec, destination="out.csv")
    ```

=== "Object with items"

    ```python
    # Automatically extracts the "items" key
    payload = '{"total": 2, "items": [{"id": 1}, {"id": 2}]}'
    generate_report(data_source=payload, spec=spec, destination="out.csv")
    ```

=== "Single object"

    ```python
    payload = '{"id": 1, "name": "Ana"}'  # auto-wrap in list
    generate_report(data_source=payload, spec=spec, destination="out.csv")
    ```

## JSON Streaming — JsonStreamingAdapter

For massive JSON files (500MB+) or I/O streams, use `JsonStreamingAdapter`. It uses the **ijson** library to read the file iteratively, keeping memory consumption constant.

```python
from {{ project_name }} import JsonStreamingAdapter, generate_report

# Reading from a file path
generate_report(
    data_source="gigantic.json",
    spec=spec,
    destination="out.csv",
    input_adapter=JsonStreamingAdapter(item_path="item")
)

# Reading from a binary stream (e.g., file object opened in 'rb')
with open("dump.json", "rb") as f:
    generate_report(
        data_source=f,
        spec=spec,
        destination="out.xlsx",
        input_adapter=JsonStreamingAdapter()
    )
```

!!! info "ijson Paths (item_path)"
    The `item_path` parameter defines where the records are located in the JSON:
    - `"item"`: For an array at the root `[{}, {}]`.
    - `"data.item"`: For an array inside a key `{"data": [{}, {}]}`.

## SQL — SqlAdapter

For SQL queries, use `SqlAdapter` explicitly:

```python
import sqlite3
from {{ project_name }} import SqlAdapter, generate_report

conn = sqlite3.connect("app.db")

generate_report(
    data_source=None,  # data comes from the adapter
    spec=spec,
    destination="out.csv",
    input_adapter=SqlAdapter(
        query="SELECT id, name, total FROM orders WHERE status = 'active'",
        connection=conn,
    ),
)
```

!!! note "Cursor Streaming"
    The `SqlAdapter` iterates over the SQL cursor without calling `fetchall()` —
    ideal for queries that return many records.

## Custom Adapter

Implement the `InputAdapter` protocol for any data source:

```python
from collections.abc import Iterable, Mapping
from typing import Any

from {{ project_name }}.contracts import InputAdapter, Record


class MongoAdapter(InputAdapter):
    def __init__(self, collection, query: dict):
        self._collection = collection
        self._query = query

    def adapt(self, data_source: Any) -> Iterable[Record]:
        for doc in self._collection.find(self._query):
            yield doc  # MongoDB docs are already dicts
```

```python
generate_report(
    data_source=None,
    spec=spec,
    destination="out.xlsx",
    input_adapter=MongoAdapter(db.orders, {"status": "active"}),
)
```

## Automatic Detection

| `data_source` type | Selected Adapter |
|----------------------|---------------------|
| `str`, `bytes`, `bytearray` | `JsonAdapter` |
| `dict` (Mapping) | `JsonAdapter` |
| Any `Iterable` | `ListDictAdapter` |
| Other | Error — pass `input_adapter` explicitly |
