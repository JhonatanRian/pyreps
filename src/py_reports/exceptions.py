class ReportError(Exception):
    """Base exception for py_reports."""


class InputAdapterError(ReportError):
    """Raised when an input adapter cannot normalize the input data."""


class MappingError(ReportError):
    """Raised when a record cannot be mapped to the report schema."""


class CoercionError(MappingError):
    """Raised when a value cannot be coerced to the declared column type."""


class RenderError(ReportError):
    """Raised when a renderer fails to produce the output file."""
