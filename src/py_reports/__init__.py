from importlib.metadata import PackageNotFoundError, version
from typing import Any

from .adapters import JsonAdapter, JsonStreamingAdapter, ListDictAdapter, SqlAdapter
from .contracts import ColumnSpec, ColumnType, DBConnection, DBCursor, ReportSpec
from .csv_options import CsvRenderOptions
from .exceptions import (
    CoercionError,
    InputAdapterError,
    MappingError,
    RenderError,
    ReportError,
)
from .service import generate_report
from .xlsx_options import XlsxRenderOptions
from .pdf_options import PdfRenderOptions


def __getattr__(name: str) -> Any:
    if name == "__version__":
        try:
            return version("py-reports")
        except PackageNotFoundError:
            return "0.0.0-dev"
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CoercionError",
    "ColumnSpec",
    "ColumnType",
    "CsvRenderOptions",
    "DBConnection",
    "DBCursor",
    "InputAdapterError",
    "JsonAdapter",
    "JsonStreamingAdapter",
    "ListDictAdapter",
    "MappingError",
    "PdfRenderOptions",
    "RenderError",
    "ReportError",
    "ReportSpec",
    "SqlAdapter",
    "XlsxRenderOptions",
    "generate_report",
    "__version__",
]
