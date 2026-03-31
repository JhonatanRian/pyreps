from __future__ import annotations

from pathlib import Path

import pytest

from py_reports import ColumnSpec, ReportSpec, generate_report


def _make_spec(**kwargs) -> ReportSpec:
    columns = kwargs.pop(
        "columns",
        [
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Nome", source="name", required=True),
            ColumnSpec(label="Total", source="total", required=True),
        ],
    )
    return ReportSpec(output_format="pdf", columns=columns, **kwargs)


def test_pdf_generates_valid_file_signature(tmp_path: Path) -> None:
    data = [{"id": "1", "name": "Ana", "total": 10.5}]
    output = generate_report(data_source=data, spec=_make_spec(), destination=tmp_path / "out.pdf")

    assert output.exists()
    assert output.suffix == ".pdf"
    assert output.read_bytes().startswith(b"%PDF-")


def test_pdf_renders_multiple_rows(tmp_path: Path) -> None:
    data = [{"id": str(i), "name": f"User {i}", "total": i * 1.5} for i in range(1, 51)]
    output = generate_report(data_source=data, spec=_make_spec(), destination=tmp_path / "out.pdf")

    assert output.stat().st_size > 0
    assert output.read_bytes().startswith(b"%PDF-")


def test_pdf_renders_empty_dataset(tmp_path: Path) -> None:
    output = generate_report(data_source=[], spec=_make_spec(), destination=tmp_path / "out.pdf")

    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF-")


def test_pdf_handles_long_cell_content(tmp_path: Path) -> None:
    data = [
        {"id": "1", "name": "x" * 500, "total": "y" * 300},
        {"id": "2", "name": "short", "total": "0"},
    ]
    output = generate_report(data_source=data, spec=_make_spec(), destination=tmp_path / "out.pdf")

    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF-")


def test_pdf_handles_none_values(tmp_path: Path) -> None:
    spec = ReportSpec(
        output_format="pdf",
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Obs", source="obs", default=None),
        ],
    )
    data = [{"id": "1"}, {"id": "2", "obs": "presente"}]
    output = generate_report(data_source=data, spec=spec, destination=tmp_path / "out.pdf")

    assert output.read_bytes().startswith(b"%PDF-")


def test_pdf_handles_special_characters(tmp_path: Path) -> None:
    data = [{"id": "1", "name": "José & Ção <test>", "total": "R$ 1.234,56"}]
    output = generate_report(data_source=data, spec=_make_spec(), destination=tmp_path / "out.pdf")

    assert output.read_bytes().startswith(b"%PDF-")


def test_pdf_creates_parent_directories(tmp_path: Path) -> None:
    destination = tmp_path / "nested" / "deep" / "report.pdf"
    data = [{"id": "1", "name": "Ana", "total": 10.0}]
    output = generate_report(data_source=data, spec=_make_spec(), destination=destination)

    assert output.exists()
