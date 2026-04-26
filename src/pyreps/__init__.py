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
from .inference import infer_report_spec
from .xlsx_options import XlsxRenderOptions
from .pdf_options import PdfRenderOptions

__version__: str
try:
    __version__ = version("pyreps")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"


def __getattr__(name: str) -> Any:
    if name == "__version__":
        return __version__
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
    "infer_report_spec",
    "__version__",
]
