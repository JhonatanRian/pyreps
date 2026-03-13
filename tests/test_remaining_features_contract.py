from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from py_reports import ColumnSpec, ReportSpec, generate_report
import py_reports.adapters as adapters_module


def _sql_adapter(query: str, connection: sqlite3.Connection) -> Any:
    sql_adapter_cls = getattr(adapters_module, "SqlAdapter", None)
    if sql_adapter_cls is None:
        pytest.fail(
            "Expected `SqlAdapter` in `py_reports.adapters` for SQL data sources."
        )
    return sql_adapter_cls(query=query, connection=connection)


def test_generate_csv_from_sql_source(tmp_path: Path) -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE sales (id TEXT PRIMARY KEY, customer_name TEXT, total REAL)"
    )
    connection.executemany(
        "INSERT INTO sales (id, customer_name, total) VALUES (?, ?, ?)",
        [("1", "Ana", 10.5), ("2", "Bruno", 20.0)],
    )
    connection.commit()

    spec = ReportSpec(
        output_format="csv",
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Cliente", source="customer_name", required=True),
            ColumnSpec(label="Total", source="total", required=True),
        ],
    )

    output = generate_report(
        data_source=None,
        spec=spec,
        destination=tmp_path / "sales_from_sql.csv",
        input_adapter=_sql_adapter(
            query="SELECT id, customer_name, total FROM sales ORDER BY id",
            connection=connection,
        ),
    )

    assert output.read_text(encoding="utf-8").splitlines() == [
        "ID,Cliente,Total",
        "1,Ana,10.5",
        "2,Bruno,20.0",
    ]


def test_generate_xlsx_file_signature(tmp_path: Path) -> None:
    data = [{"id": "1", "customer": {"name": "Ana"}, "total": 10.5}]
    spec = ReportSpec(
        output_format="xlsx",
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Cliente", source="customer.name", required=True),
            ColumnSpec(label="Total", source="total", required=True),
        ],
    )

    output = generate_report(
        data_source=data,
        spec=spec,
        destination=tmp_path / "sales.xlsx",
    )

    assert output.exists()
    assert output.suffix == ".xlsx"
    # XLSX is a zip container, so files should start with PK signature.
    assert output.read_bytes()[:2] == b"PK"


def test_generate_pdf_file_signature(tmp_path: Path) -> None:
    data = [{"id": "1", "customer": {"name": "Ana"}, "total": 10.5}]
    spec = ReportSpec(
        output_format="pdf",
        columns=[
            ColumnSpec(label="ID", source="id", required=True),
            ColumnSpec(label="Cliente", source="customer.name", required=True),
            ColumnSpec(label="Total", source="total", required=True),
        ],
    )

    output = generate_report(
        data_source=data,
        spec=spec,
        destination=tmp_path / "sales.pdf",
    )

    assert output.exists()
    assert output.suffix == ".pdf"
    assert output.read_bytes().startswith(b"%PDF-")
