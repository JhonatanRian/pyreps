from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import load_workbook

from py_reports import ColumnSpec, ReportSpec, generate_report
from py_reports.exceptions import ReportError


def test_xlsx_manual_width_respected(tmp_path: Path) -> None:
    data = [{"id": "1", "customer": {"name": "Ana"}}]
    spec = ReportSpec(
        output_format="xlsx",
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Cliente", source="customer.name", required=True),
        ],
        metadata={
            "xlsx": {
                "width_mode": "manual",
                "columns": {"ID": {"width": 30}},
            }
        },
    )

    output = generate_report(data_source=data, spec=spec, destination=tmp_path / "manual.xlsx")

    assert _column_width(output, "A") == pytest.approx(30.0, abs=0.1)


def test_xlsx_auto_width_grows_for_long_content(tmp_path: Path) -> None:
    data = [{"id": "1", "customer": {"name": "Cliente Com Nome Bem Longo"}}]
    spec = ReportSpec(
        output_format="xlsx",
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Cliente", source="customer.name", required=True),
        ],
        metadata={
            "xlsx": {
                "width_mode": "auto",
                "default_width": 8,
                "auto_padding": 2,
            }
        },
    )

    output = generate_report(data_source=data, spec=spec, destination=tmp_path / "auto.xlsx")

    assert _column_width(output, "B") > 8.0


def test_xlsx_mixed_mode_prefers_explicit_column_width(tmp_path: Path) -> None:
    data = [{"id": "1234567890", "customer": {"name": "Cliente com nome muito muito longo"}}]
    spec = ReportSpec(
        output_format="xlsx",
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Cliente", source="customer.name", required=True),
        ],
        metadata={
            "xlsx": {
                "width_mode": "mixed",
                "columns": {"ID": {"width": 9}},
            }
        },
    )

    output = generate_report(data_source=data, spec=spec, destination=tmp_path / "mixed.xlsx")

    assert _column_width(output, "A") == pytest.approx(9.0, abs=0.1)


def test_xlsx_auto_width_respects_min_and_max_clamp(tmp_path: Path) -> None:
    data = [{"id": "1", "customer": {"name": "curto"}}]
    spec = ReportSpec(
        output_format="xlsx",
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Cliente", source="customer.name", required=True),
        ],
        metadata={
            "xlsx": {
                "width_mode": "auto",
                "columns": {
                    "Cliente": {"min_width": 14, "max_width": 16},
                },
            }
        },
    )

    output = generate_report(data_source=data, spec=spec, destination=tmp_path / "clamp.xlsx")

    width = _column_width(output, "B")
    assert width >= 14.0
    assert width <= 16.0


def test_xlsx_manual_mode_falls_back_to_default_width(tmp_path: Path) -> None:
    data = [{"id": "1"}]
    spec = ReportSpec(
        output_format="xlsx",
        columns=[ColumnSpec(label="ID", source="id", required=True)],
        metadata={"xlsx": {"width_mode": "manual", "default_width": 18}},
    )

    output = generate_report(data_source=data, spec=spec, destination=tmp_path / "default.xlsx")

    assert _column_width(output, "A") == pytest.approx(18.0, abs=0.1)


def test_xlsx_invalid_width_mode_raises_report_error(tmp_path: Path) -> None:
    data = [{"id": "1"}]
    spec = ReportSpec(
        output_format="xlsx",
        columns=[ColumnSpec(label="ID", source="id", required=True)],
        metadata={"xlsx": {"width_mode": "invalid"}},
    )

    with pytest.raises(ReportError):
        generate_report(data_source=data, spec=spec, destination=tmp_path / "invalid.xlsx")


def _column_width(path: Path, column_letter: str) -> float:
    workbook = load_workbook(path)
    worksheet = workbook.active
    width = worksheet.column_dimensions[column_letter].width
    return float(width if width is not None else 0.0)
