import pytest
from pyreps.utils.records import ensure_mapping_stream, WidthTracker, TupleRecord
from pyreps.exceptions import InputAdapterError


def test_tuple_record_methods():
    col_map = {"a": 0, "b": 1}
    row = (10, 20)
    record = TupleRecord(col_map, row)

    assert record["a"] == 10
    assert record.get("a") == 10
    assert record.get("c", 30) == 30
    assert len(record) == 2
    assert list(record) == ["a", "b"]


def test_width_tracker_handles_none():
    rows = [{"a": "hi"}, {"a": None}, {"a": "world"}]
    tracker = WidthTracker(rows, labels=["a"])
    list(tracker)
    assert tracker.max_lens["a"] == 5  # "world" is 5


def test_ensure_mapping_stream_empty():
    iterator = iter([])
    result = list(ensure_mapping_stream(iterator))
    assert result == []


def test_ensure_mapping_stream_invalid_first():
    iterator = iter([1, 2, 3])
    with pytest.raises(InputAdapterError, match="Input record must be a mapping"):
        list(ensure_mapping_stream(iterator))


def test_width_tracker_no_labels():
    rows = [{"a": 1}, {"a": 2}]
    tracker = WidthTracker(rows, labels=[])
    result = list(tracker)
    assert result == rows


def test_width_tracker_single_label():
    rows = [{"a": "hello"}, {"a": "world!!"}]
    tracker = WidthTracker(rows, labels=["a"])
    result = list(tracker)
    assert result == rows
    assert tracker.max_lens["a"] == 7  # "world!!" is 7 chars
