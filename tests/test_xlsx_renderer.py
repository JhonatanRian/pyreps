from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest import mock

import pytest
from openpyxl import load_workbook

from py_reports import ColumnSpec, ReportSpec, generate_report
from py_reports.exceptions import RenderError, ReportError
from py_reports.renderers import XLSX_NS as _XLSX_NS
from py_reports.renderers import _SHEET_PATH


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


def _assert_xlsx_xml_integrity(path: Path, *, expect_cols: bool) -> None:
    """Validate XLSX ZIP structure and XML well-formedness."""
    with zipfile.ZipFile(path, "r") as zf:
        assert zf.testzip() is None, "XLSX ZIP is corrupted"
        assert _SHEET_PATH in zf.namelist(), "sheet1.xml missing from XLSX"

        sheet_xml = zf.read(_SHEET_PATH)
        root = ET.fromstring(sheet_xml)  # will raise on malformed XML

        ns = {"ns": _XLSX_NS}
        cols = root.findall("ns:cols", ns)
        sheet_data = root.find("ns:sheetData", ns)

        if expect_cols:
            assert len(cols) == 1, f"Expected exactly 1 <cols>, found {len(cols)}"
            # <cols> must appear before <sheetData>
            children = list(root)
            cols_idx = children.index(cols[0])
            data_idx = children.index(sheet_data)
            assert cols_idx < data_idx, "<cols> must appear before <sheetData>"

        assert sheet_data is not None, "<sheetData> missing from sheet XML"


def test_xlsx_dom_patch_produces_valid_xml(tmp_path: Path) -> None:
    """XLSX with per-column overrides uses DOM patching — validate XML integrity."""
    data = [{"id": "1", "customer": {"name": "Ana"}}]
    spec = ReportSpec(
        output_format="xlsx",
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Cliente", source="customer.name", required=True),
        ],
        metadata={
            "xlsx": {
                "width_mode": "mixed",
                "columns": {"ID": {"width": 20}},
            }
        },
    )

    output = generate_report(data_source=data, spec=spec, destination=tmp_path / "dom.xlsx")
    _assert_xlsx_xml_integrity(output, expect_cols=True)


def test_xlsx_pure_autofit_produces_valid_xml(tmp_path: Path) -> None:
    """XLSX with pure auto mode (no overrides) — no DOM patch, still valid XML."""
    data = [{"id": "1", "customer": {"name": "Ana"}}]
    spec = ReportSpec(
        output_format="xlsx",
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Cliente", source="customer.name", required=True),
        ],
        metadata={"xlsx": {"width_mode": "auto"}},
    )

    output = generate_report(data_source=data, spec=spec, destination=tmp_path / "autofit.xlsx")
    _assert_xlsx_xml_integrity(output, expect_cols=False)


def test_xlsx_tmp_file_cleaned_up_on_error(tmp_path: Path) -> None:
    """Ensure .tmp.xlsx is deleted if an error occurs during streaming patch."""
    data = [{"id": "1"}]
    spec = ReportSpec(
        output_format="xlsx",
        columns=[ColumnSpec(label="ID", source="id", required=True)],
        metadata={
            "xlsx": {
                "width_mode": "mixed",
                "columns": {"ID": {"width": 20}},
            }
        },
    )
    dest = tmp_path / "leak_test.xlsx"

    # Mock _stream_patch_sheet_xml to raise an error during the patching phase
    with mock.patch("py_reports.renderers._stream_patch_sheet_xml", side_effect=RuntimeError("Simulated Leak")):
        with pytest.raises(RenderError, match="Simulated Leak"):
            generate_report(data_source=data, spec=spec, destination=dest)

    # Verify tmp file is gone
    tmp_file = dest.with_suffix(".tmp.xlsx")
    assert not tmp_file.exists(), "Temporary file leaked!"


def test_xlsx_stream_patch_tag_boundary() -> None:
    """Stress test: tag <sheetData> split exactly across 64KB chunk boundaries."""
    import io
    from py_reports.renderers import _stream_patch_sheet_xml

    # chunk_size in _stream_patch_sheet_xml is 65536
    chunk_size = 65536
    
    # We position "<sheetData>" so "<she" (4 chars) is at the end of the first chunk
    # and "etData>" is at the start of the second chunk.
    prefix = b"A" * (chunk_size - 4)
    xml_content = prefix + b"<sheetData><row/></sheetData>"
    
    instream = io.BytesIO(xml_content)
    outstream = io.BytesIO()
    cols_el = ET.Element(f"{{{_XLSX_NS}}}cols")
    ET.SubElement(cols_el, f"{{{_XLSX_NS}}}col", {"min": "1", "max": "1", "width": "20"})
    
    # Run the streaming patcher
    _stream_patch_sheet_xml(instream, outstream, cols_el)
    
    result = outstream.getvalue()
    
    # Check if patch was successful
    assert b"<cols" in result, "Patch failed: <cols> tag missing"
    assert b"<sheetData" in result, "Data corrupted: <sheetData> tag missing"
    # Ensure relative order
    assert result.find(b"<cols") < result.find(b"<sheetData"), "<cols> must be before <sheetData>"
    # Ensure content was preserved
    assert b"<row/>" in result
