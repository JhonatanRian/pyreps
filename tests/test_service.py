from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyreps import ColumnSpec, ReportSpec, generate_report
from pyreps.contracts import InputAdapter, Renderer
from pyreps.exceptions import InputAdapterError, ReportError
from pyreps.renderers import default_renderer_registry


def test_generate_csv_from_list_dict(tmp_path: Path) -> None:
    data = [
        {"id": "1", "customer": {"name": "Ana"}, "total": 10.5},
        {"id": "2", "customer": {"name": "Bruno"}, "total": 20.0},
    ]
    spec = ReportSpec(
        output_format="csv",
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Cliente", source="customer.name", required=True),
            ColumnSpec(
                label="Total", source="total", formatter=lambda value: f"{value:.2f}"
            ),
        ],
    )

    output = generate_report(
        data_source=data, spec=spec, destination=tmp_path / "sales.csv"
    )

    assert output.exists()
    assert output.read_text(encoding="utf-8").splitlines() == [
        "ID,Cliente,Total",
        "1,Ana,10.50",
        "2,Bruno,20.00",
    ]


def test_generate_csv_from_json_payload(tmp_path: Path) -> None:
    payload = json.dumps(
        [
            {"id": "1", "customer": {"name": "Ana"}},
            {"id": "2", "customer": {"name": "Bruno"}},
        ]
    )
    spec = ReportSpec(
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Cliente", source="customer.name", required=True),
        ]
    )

    output = generate_report(
        data_source=payload, spec=spec, destination=tmp_path / "customers.csv"
    )

    assert output.read_text(encoding="utf-8").splitlines() == [
        "ID,Cliente",
        "1,Ana",
        "2,Bruno",
    ]


def test_generate_csv_uses_delimiter_from_metadata(tmp_path: Path) -> None:
    data = [{"id": "1", "customer": {"name": "Ana"}}]
    spec = ReportSpec(
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Cliente", source="customer.name", required=True),
        ],
        metadata={"csv": {"delimiter": ";"}},
    )

    output = generate_report(
        data_source=data, spec=spec, destination=tmp_path / "delimited.csv"
    )

    assert output.read_text(encoding="utf-8").splitlines() == [
        "ID;Cliente",
        "1;Ana",
    ]


def test_non_supported_data_source_requires_explicit_adapter(tmp_path: Path) -> None:
    spec = ReportSpec(columns=[ColumnSpec(label="ID", source="id")])

    with pytest.raises(InputAdapterError):
        generate_report(
            data_source=123, spec=spec, destination=tmp_path / "invalid.csv"
        )


def test_can_inject_custom_input_adapter(tmp_path: Path) -> None:
    class CustomAdapter(InputAdapter):
        def adapt(self, data_source: object):
            return [{"id": "A-1"}]

    spec = ReportSpec(columns=[ColumnSpec(label="ID", source="id", required=True)])
    output = generate_report(
        data_source=object(),
        spec=spec,
        destination=tmp_path / "custom.csv",
        input_adapter=CustomAdapter(),
    )

    assert output.read_text(encoding="utf-8").splitlines() == ["ID", "A-1"]


def test_default_registry_exposes_all_output_formats() -> None:
    registry = default_renderer_registry()
    assert set(registry.keys()) == {"csv", "xlsx", "pdf"}


def test_pdf_renderer_generates_valid_file(tmp_path: Path) -> None:
    data = [{"id": "1"}]
    spec = ReportSpec(
        output_format="pdf", columns=[ColumnSpec(label="ID", source="id")]
    )

    output = generate_report(
        data_source=data, spec=spec, destination=tmp_path / "report.pdf"
    )

    assert output.exists()
    assert output.suffix == ".pdf"
    assert output.read_bytes().startswith(b"%PDF-")


def test_missing_renderer_registration_raises_report_error(tmp_path: Path) -> None:
    data = [{"id": "1"}]
    spec = ReportSpec(columns=[ColumnSpec(label="ID", source="id", required=True)])
    registry_without_csv = {"xlsx": default_renderer_registry()["xlsx"]}

    with pytest.raises(ReportError):
        generate_report(
            data_source=data,
            spec=spec,
            destination=tmp_path / "report.csv",
            renderer_registry=registry_without_csv,
        )


def test_generate_report_emits_logs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("DEBUG", logger="pyreps")
    data = [{"id": "1"}]
    spec = ReportSpec(columns=[ColumnSpec(label="ID", source="id")])
    destination = tmp_path / "logged.csv"

    generate_report(data_source=data, spec=spec, destination=destination)

    assert "adapter resolved: ListDictAdapter" in caplog.text
    assert "report generated: format=csv" in caplog.text
    assert f"destination={destination}" in caplog.text


def test_generate_report_removes_partial_file_on_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    class CrashingRenderer(Renderer):
        def render(self, rows, spec, destination, progress_context):
            path = Path(destination)
            path.write_text("partial data")
            raise RuntimeError("something went wrong")

    data = [{"id": "1"}]
    spec = ReportSpec(
        output_format="csv", columns=[ColumnSpec(label="ID", source="id")]
    )
    destination = tmp_path / "fail.txt"
    registry = {"csv": CrashingRenderer()}

    with pytest.raises(RuntimeError, match="something went wrong"):
        generate_report(
            data_source=data,
            spec=spec,
            destination=destination,
            renderer_registry=registry,
        )

    assert not destination.exists()
    assert "report generation failed" in caplog.text
    assert f"destination={destination}" in caplog.text
    assert "error_type=RuntimeError" in caplog.text
