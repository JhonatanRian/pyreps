from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar


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


F = TypeVar("F", bound=Callable[..., Any])


def wrap_render_error(format_name: str) -> Callable[[F], F]:
    """Decorator to wrap any exception during rendering into a RenderError."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                if isinstance(exc, RenderError):
                    raise exc
                raise RenderError(f"Failed to render {format_name}: {exc}") from exc

        return wrapper  # type: ignore

    return decorator
