class ReportError(Exception):
    """Base exception for py_reports."""


class InputAdapterError(ReportError):
    """Raised when an input adapter cannot normalize the input data."""


class MappingError(ReportError):
    """Raised when a record cannot be mapped to the report schema."""
