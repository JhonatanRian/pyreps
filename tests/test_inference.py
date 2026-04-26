import json
from datetime import date, datetime
from pyreps.adapters import ListDictAdapter
from pyreps.contracts import ReportSpec
from pyreps.inference import infer_report_spec, _detect_type
from pyreps.utils.records import flatten_record


def test_flatten_record():
    record = {
        "id": 1,
        "user": {
            "name": "Alice",
            "address": {
                "city": "Wonderland",
                "zip": "12345"
            }
        },
        "tags": ["a", "b"]
    }
    flattened = dict(flatten_record(record))
    assert flattened == {
        "id": 1,
        "user.name": "Alice",
        "user.address.city": "Wonderland",
        "user.address.zip": "12345",
        "tags": ["a", "b"]
    }


def test_detect_type():
    assert _detect_type([True, False, None], "col") == "bool"
    assert _detect_type(["true", "false", "yes", "no"], "col") == "bool"
    assert _detect_type([1, 2, 3, None], "col") == "int"
    assert _detect_type(["1", "2", "3"], "col") == "int"
    assert _detect_type([1.5, 2, 3], "col") == "float"
    assert _detect_type(["1.5", "2"], "col") == "float"
    assert _detect_type(["2023-01-01", "2023-12-31"], "col") == "date"
    assert _detect_type(["01/01/2023", date(2023, 1, 1)], "col") == "date"
    assert _detect_type(["2023-01-01T10:00:00", datetime(2023, 1, 1, 10)], "col") == "datetime"
    assert _detect_type(["Alice", "Bob", "123"], "col") == "str"


def test_infer_report_spec():
    data = [
        {
            "id": 1,
            "created_at": "2023-01-01T10:00:00",
            "metadata": {"score": 95.5, "active": "yes"},
            "user": {"name": "Alice"}
        },
        {
            "id": 2,
            "created_at": "2023-01-02T11:00:00",
            "metadata": {"score": 88.0, "active": "no"},
            "user": {"name": "Bob"}
        }
    ]
    adapter = ListDictAdapter()
    spec = infer_report_spec(adapter, data)

    assert isinstance(spec, ReportSpec)
    assert spec.output_format == "csv"
    
    # Check columns (sorted alphabetically by key in infer_report_spec)
    # Keys: created_at, id, metadata.active, metadata.score, user.name
    cols = {col.source: col for col in spec.columns}
    
    assert cols["id"].type == "int"
    assert cols["id"].label == "Id"
    
    assert cols["created_at"].type == "datetime"
    assert cols["created_at"].label == "Created At"
    
    assert cols["metadata.score"].type == "float"
    assert cols["metadata.score"].label == "Metadata Score"
    
    assert cols["metadata.active"].type == "bool"
    assert cols["metadata.active"].label == "Metadata Active"
    
    assert cols["user.name"].type == "str"
    assert cols["user.name"].label == "User Name"


def test_spec_to_dict_serialization():
    data = [{"a": 1, "b": "2023-01-01"}]
    adapter = ListDictAdapter()
    spec = infer_report_spec(adapter, data)
    d = spec.to_dict()
    
    # Verify it can be dumped to JSON
    json_str = json.dumps(d)
    assert "output_format" in json_str
    assert "columns" in json_str
    
    # Load back and check
    loaded = json.loads(json_str)
    assert loaded["output_format"] == "csv"
    assert len(loaded["columns"]) == 2
    sources = [c["source"] for c in loaded["columns"]]
    assert "a" in sources
    assert "b" in sources
