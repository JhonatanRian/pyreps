from __future__ import annotations

import pytest

from py_reports import ColumnSpec, ReportSpec
from py_reports.exceptions import MappingError
from py_reports.mapping import map_records


def test_map_records_maps_nested_paths() -> None:
    records = [{"customer": {"name": "Ana"}, "id": "1"}]
    spec = ReportSpec(
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Cliente", source="customer.name", required=True),
        ]
    )

    rows = list(map_records(records, spec))

    assert rows == [{"ID": "1", "Cliente": "Ana"}]


def test_map_records_applies_default_value() -> None:
    records = [{"id": "1"}]
    spec = ReportSpec(
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Status", source="status", default="Pendente"),
        ]
    )

    rows = list(map_records(records, spec))

    assert rows == [{"ID": "1", "Status": "Pendente"}]


def test_map_records_applies_formatter() -> None:
    records = [{"id": "1", "total": 10.5}]
    spec = ReportSpec(
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Total", source="total", formatter=lambda value: f"{value:.2f}"),
        ]
    )

    rows = list(map_records(records, spec))

    assert rows == [{"ID": "1", "Total": "10.50"}]


def test_map_records_raises_for_missing_required_field() -> None:
    records = [{"id": "1"}]
    spec = ReportSpec(columns=[ColumnSpec(label="Cliente", source="customer.name", required=True)])

    with pytest.raises(MappingError):
        list(map_records(records, spec))
