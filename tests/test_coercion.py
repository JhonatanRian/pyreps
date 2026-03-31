from __future__ import annotations

from datetime import date, datetime

import pytest

from py_reports import ColumnSpec, ReportSpec
from py_reports.exceptions import MappingError
from py_reports.mapping import map_records


# ── str coercion ──────────────────────────────────────────────────────

def test_coerce_str_from_int() -> None:
    rows = _map([{"v": 42}], type="str", source="v")
    assert rows == [{"out": "42"}]


def test_coerce_str_from_float() -> None:
    rows = _map([{"v": 3.14}], type="str", source="v")
    assert rows == [{"out": "3.14"}]


def test_coerce_str_from_bool() -> None:
    rows = _map([{"v": True}], type="str", source="v")
    assert rows == [{"out": "True"}]


def test_coerce_str_from_none_passthrough() -> None:
    rows = _map([{"v": None}], type="str", source="v")
    assert rows == [{"out": None}]


# ── int coercion ──────────────────────────────────────────────────────

def test_coerce_int_identity() -> None:
    rows = _map([{"v": 42}], type="int", source="v")
    assert rows == [{"out": 42}]


def test_coerce_int_from_string() -> None:
    rows = _map([{"v": "7"}], type="int", source="v")
    assert rows == [{"out": 7}]


def test_coerce_int_from_string_with_whitespace() -> None:
    rows = _map([{"v": " 7 "}], type="int", source="v")
    assert rows == [{"out": 7}]


def test_coerce_int_from_bool() -> None:
    rows = _map([{"v": True}], type="int", source="v")
    assert rows == [{"out": 1}]


def test_coerce_int_from_float_lossless() -> None:
    rows = _map([{"v": 5.0}], type="int", source="v")
    assert rows == [{"out": 5}]


def test_coerce_int_from_float_lossy_raises() -> None:
    with pytest.raises(MappingError, match="cannot coerce"):
        _map([{"v": 5.7}], type="int", source="v")


def test_coerce_int_from_invalid_string_raises() -> None:
    with pytest.raises(MappingError, match="cannot coerce"):
        _map([{"v": "abc"}], type="int", source="v")


# ── float coercion ────────────────────────────────────────────────────

def test_coerce_float_identity() -> None:
    rows = _map([{"v": 3.14}], type="float", source="v")
    assert rows == [{"out": pytest.approx(3.14)}]


def test_coerce_float_from_string() -> None:
    rows = _map([{"v": "3.14"}], type="float", source="v")
    assert rows == [{"out": pytest.approx(3.14)}]


def test_coerce_float_from_string_with_whitespace() -> None:
    rows = _map([{"v": " 3.14 "}], type="float", source="v")
    assert rows == [{"out": pytest.approx(3.14)}]


def test_coerce_float_from_int() -> None:
    rows = _map([{"v": 10}], type="float", source="v")
    assert rows == [{"out": 10.0}]


def test_coerce_float_from_invalid_string_raises() -> None:
    with pytest.raises(MappingError, match="cannot coerce"):
        _map([{"v": "abc"}], type="float", source="v")


# ── bool coercion ─────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("true", True), ("True", True), ("1", True), ("yes", True), ("sim", True),
    ("false", False), ("False", False), ("0", False), ("no", False), ("não", False),
])
def test_coerce_bool_from_string(raw: str, expected: bool) -> None:
    rows = _map([{"v": raw}], type="bool", source="v")
    assert rows == [{"out": expected}]


def test_coerce_bool_identity() -> None:
    rows = _map([{"v": False}], type="bool", source="v")
    assert rows == [{"out": False}]


def test_coerce_bool_from_int() -> None:
    rows = _map([{"v": 1}], type="bool", source="v")
    assert rows == [{"out": True}]


def test_coerce_bool_from_int_zero() -> None:
    rows = _map([{"v": 0}], type="bool", source="v")
    assert rows == [{"out": False}]


def test_coerce_bool_from_float() -> None:
    rows = _map([{"v": 0.0}], type="bool", source="v")
    assert rows == [{"out": False}]


def test_coerce_bool_invalid_string_raises() -> None:
    with pytest.raises(MappingError, match="cannot coerce"):
        _map([{"v": "maybe"}], type="bool", source="v")


def test_coerce_bool_unsupported_type_raises() -> None:
    with pytest.raises(MappingError, match="cannot coerce"):
        _map([{"v": [1, 2]}], type="bool", source="v")


# ── date coercion ─────────────────────────────────────────────────────

def test_coerce_date_from_iso_string() -> None:
    rows = _map([{"v": "2025-06-15"}], type="date", source="v")
    assert rows == [{"out": date(2025, 6, 15)}]


def test_coerce_date_from_br_string() -> None:
    rows = _map([{"v": "15/06/2025"}], type="date", source="v")
    assert rows == [{"out": date(2025, 6, 15)}]


def test_coerce_date_from_datetime_strips_time() -> None:
    rows = _map([{"v": datetime(2025, 6, 15, 10, 30)}], type="date", source="v")
    assert rows == [{"out": date(2025, 6, 15)}]


def test_coerce_date_from_date_object() -> None:
    rows = _map([{"v": date(2025, 1, 1)}], type="date", source="v")
    assert rows == [{"out": date(2025, 1, 1)}]


def test_coerce_date_invalid_string_raises() -> None:
    with pytest.raises(MappingError, match="cannot coerce"):
        _map([{"v": "not-a-date"}], type="date", source="v")


def test_coerce_date_unsupported_type_raises() -> None:
    with pytest.raises(MappingError, match="cannot coerce"):
        _map([{"v": 12345}], type="date", source="v")


# ── datetime coercion ─────────────────────────────────────────────────

def test_coerce_datetime_identity() -> None:
    dt = datetime(2025, 6, 15, 10, 30)
    rows = _map([{"v": dt}], type="datetime", source="v")
    assert rows == [{"out": dt}]


def test_coerce_datetime_from_iso_string() -> None:
    rows = _map([{"v": "2025-06-15T10:30:00"}], type="datetime", source="v")
    assert rows == [{"out": datetime(2025, 6, 15, 10, 30)}]


def test_coerce_datetime_from_space_separated_string() -> None:
    rows = _map([{"v": "2025-06-15 10:30:00"}], type="datetime", source="v")
    assert rows == [{"out": datetime(2025, 6, 15, 10, 30)}]


def test_coerce_datetime_from_date_object() -> None:
    rows = _map([{"v": date(2025, 6, 15)}], type="datetime", source="v")
    assert rows == [{"out": datetime(2025, 6, 15)}]


def test_coerce_datetime_invalid_string_raises() -> None:
    with pytest.raises(MappingError, match="cannot coerce"):
        _map([{"v": "not-a-datetime"}], type="datetime", source="v")


def test_coerce_datetime_unsupported_type_raises() -> None:
    with pytest.raises(MappingError, match="cannot coerce"):
        _map([{"v": 12345}], type="datetime", source="v")


# ── interaction with formatter ────────────────────────────────────────

def test_type_coercion_runs_before_formatter() -> None:
    """Formatter receives the coerced value (date object, not string)."""
    spec = ReportSpec(columns=[
        ColumnSpec(
            label="out",
            source="v",
            type="date",
            formatter=lambda d: d.strftime("%d/%m/%Y"),
        ),
    ])
    rows = map_records([{"v": "2025-06-15"}], spec)
    assert rows == [{"out": "15/06/2025"}]


# ── no type = passthrough (backwards compatible) ──────────────────────

def test_no_type_passes_value_through() -> None:
    rows = _map([{"v": {"nested": True}}], type=None, source="v")
    assert rows == [{"out": {"nested": True}}]


# ── default value with type ──────────────────────────────────────────

def test_default_value_typed_correctly_passes_through() -> None:
    spec = ReportSpec(columns=[
        ColumnSpec(label="out", source="missing", type="int", default=0),
    ])
    rows = map_records([{"other": "x"}], spec)
    assert rows == [{"out": 0}]


def test_default_string_value_is_coerced_by_type() -> None:
    """Default values are also subject to coercion when type is set."""
    spec = ReportSpec(columns=[
        ColumnSpec(label="out", source="missing", type="int", default="42"),
    ])
    rows = map_records([{"other": "x"}], spec)
    assert rows == [{"out": 42}]


def test_default_none_skips_coercion() -> None:
    spec = ReportSpec(columns=[
        ColumnSpec(label="out", source="missing", type="int", default=None),
    ])
    rows = map_records([{"other": "x"}], spec)
    assert rows == [{"out": None}]


# ── required + type interaction ──────────────────────────────────────

def test_required_field_with_type_coerces_value() -> None:
    spec = ReportSpec(columns=[
        ColumnSpec(label="out", source="v", type="int", required=True),
    ])
    rows = map_records([{"v": "10"}], spec)
    assert rows == [{"out": 10}]


def test_required_missing_raises_before_coercion() -> None:
    spec = ReportSpec(columns=[
        ColumnSpec(label="out", source="v", type="int", required=True),
    ])
    with pytest.raises(MappingError, match="required field"):
        map_records([{"other": "x"}], spec)


# ── multiple records ─────────────────────────────────────────────────

def test_coercion_applies_to_all_records() -> None:
    records = [{"v": "1"}, {"v": "2"}, {"v": "3"}]
    rows = _map(records, type="int", source="v")
    assert rows == [{"out": 1}, {"out": 2}, {"out": 3}]


def test_coercion_error_reports_correct_record_index() -> None:
    records = [{"v": "1"}, {"v": "bad"}, {"v": "3"}]
    with pytest.raises(MappingError, match="record index 1"):
        _map(records, type="int", source="v")


# ── helper ────────────────────────────────────────────────────────────

def _map(records: list[dict], *, type: str | None, source: str) -> list[dict]:
    spec = ReportSpec(columns=[ColumnSpec(label="out", source=source, type=type)])
    return map_records(records, spec)
