from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyreps.contracts import ReportSpec, ColumnSpec, NullProgressContext
from pyreps.renderers import CsvRenderer, XlsxRenderer, PdfRenderer
from pyreps.utils.files import is_remote_path


@pytest.fixture
def spec():
    return ReportSpec(
        columns=(
            ColumnSpec(label="name", source="name"),
            ColumnSpec(label="age", source="age"),
        ),
        output_format="csv",
    )


@pytest.fixture
def rows():
    return [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]


def test_is_remote_path():
    assert is_remote_path("s3://bucket/file.csv") is True
    assert is_remote_path("gcs://bucket/file.csv") is True
    assert is_remote_path("abfs://container/file.csv") is True
    assert is_remote_path("c:/local/file.csv") is False
    assert is_remote_path("/local/file.csv") is False
    assert is_remote_path(Path("/local/file.csv")) is False


@patch("fsspec.open")
def test_csv_renderer_remote(mock_fsspec_open, spec, rows):
    mock_handle = MagicMock()
    mock_fsspec_open.return_value.__enter__.return_value = mock_handle
    
    renderer = CsvRenderer()
    destination = "s3://bucket/test.csv"
    
    result = renderer.render(rows, spec, destination, NullProgressContext())
    
    assert result == destination
    mock_fsspec_open.assert_called_once_with(destination, "w", newline="", encoding="utf-8")
    # Verify that it wrote something (header + 2 rows)
    assert mock_handle.write.called


@patch("fsspec.open")
@patch("fsspec.core.url_to_fs")
def test_xlsx_renderer_remote(mock_url_to_fs, mock_fsspec_open, rows):
    mock_fs = MagicMock()
    mock_url_to_fs.return_value = (mock_fs, "bucket/test.xlsx")
    
    mock_handle = MagicMock()
    mock_fsspec_open.return_value.__enter__.return_value = mock_handle
    
    spec = ReportSpec(
        columns=(ColumnSpec(label="name", source="name"),),
        output_format="xlsx",
    )
    renderer = XlsxRenderer()
    destination = "s3://bucket/test.xlsx"
    
    result = renderer.render(rows, spec, destination, NullProgressContext())
    
    assert result == destination
    assert mock_url_to_fs.called
    assert mock_fs.put.called


@patch("fsspec.open")
@patch("fsspec.core.url_to_fs")
def test_pdf_renderer_remote(mock_url_to_fs, mock_fsspec_open, rows):
    mock_fs = MagicMock()
    mock_url_to_fs.return_value = (mock_fs, "bucket/test.pdf")
    
    mock_handle = MagicMock()
    mock_fsspec_open.return_value.__enter__.return_value = mock_handle
    
    spec = ReportSpec(
        columns=(ColumnSpec(label="name", source="name"),),
        output_format="pdf",
    )
    renderer = PdfRenderer()
    destination = "s3://bucket/test.pdf"
    
    result = renderer.render(rows, spec, destination, NullProgressContext())
    
    assert result == destination
    assert mock_url_to_fs.called
    assert mock_fs.put.called
