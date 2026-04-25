from __future__ import annotations

from pathlib import Path

import pytest

from pyreps import ColumnSpec, ReportSpec, generate_report


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


def test_pdf_respects_custom_chunk_size(tmp_path: Path) -> None:
    """Custom chunk_size via metadata[\"pdf\"][\"chunk_size\"] produces valid PDFs."""
    data = [{"id": str(i), "name": f"User {i}", "total": i * 1.5} for i in range(1, 21)]
    spec = _make_spec(metadata={"pdf": {"chunk_size": 5}})
    output = generate_report(data_source=data, spec=spec, destination=tmp_path / "out.pdf")

    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF-")


def test_pdf_odd_chunk_size_alternating_backgrounds(tmp_path: Path) -> None:
    """Verify that PDF generation works with an odd chunk_size across boundaries."""
    # Data with 12 rows, chunk_size=5.
    # Chunk 1: rows 0-4 (5 rows)
    # Chunk 2: rows 5-9 (5 rows)
    # Chunk 3: rows 10-11 (2 rows)
    data = [{"id": str(i), "name": f"User {i}", "total": i} for i in range(1, 13)]
    spec = _make_spec(metadata={"pdf": {"chunk_size": 5}})
    output = generate_report(data_source=data, spec=spec, destination=tmp_path / "odd_chunk.pdf")

    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF-")


def test_resolve_pdf_column_widths_robustness() -> None:
    """Verify that _resolve_pdf_column_widths handles datasets that would cause negative widths."""
    from pyreps.renderers import _resolve_pdf_column_widths

    # Scenario: 7 columns where 1 has a tiny surplus and 6 have a deficit.
    # available_width = 200, _MIN_WIDTH_PT = 30.
    # Total required min width = 210.
    labels = ["LongLabel" + "x" * 23] + ["Short"] * 6
    # char_widths will be [32, 5, 5, 5, 5, 5, 5] if no data.
    # Let's force char_widths to be [32, 28, 28, 28, 28, 28, 28] by providing data rows.
    data_rows = [["x" * 32] + ["x" * 28] * 6]
    available_width = 200.0

    widths = _resolve_pdf_column_widths(labels, data_rows, available_width)

    # All columns should be at least _MIN_WIDTH_PT (30.0)
    assert all(w >= 30.0 for w in widths), f"Expected all widths >= 30.0, got {widths}"

    # Sum should be exactly 210.0 in this specific edge case (all at min)
    assert abs(sum(widths) - 210.0) < 1e-6
