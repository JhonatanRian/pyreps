from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Mapping, Protocol

OutputFormat = Literal["csv", "xlsx", "pdf"]
ColumnType = Literal["str", "int", "float", "bool", "date", "datetime"]
Record = Mapping[str, Any]
Formatter = Callable[[Any], Any]


@dataclass(slots=True, frozen=True)
class ColumnSpec:
    """
    Configuration for a single report column.

    Attributes:
        label: The display name of the column (used as header).
        source: The key in the input record to fetch data from. Can use dot notation (e.g., 'user.name').
        required: If True, raises MappingError if the source key is missing.
        default: Default value to use if the source key is missing and not required.
        formatter: Optional callable to transform the value after mapping and coercion.
        type: Optional type to coerce to. Allowed: 'str', 'int', 'float', 'bool', 'date', 'datetime'.
    """

    label: str
    source: str
    required: bool = False
    default: Any = None
    formatter: Formatter | None = None
    type: ColumnType | None = None
    _source_parts: tuple[str, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Pre-split source for performance in mapping hot-path
        object.__setattr__(self, "_source_parts", tuple(self.source.split(".")))


@dataclass(slots=True, frozen=True)
class ReportSpec:
    """
    Complete specification for a report generation.

    Attributes:
        columns: List of ColumnSpec defining the report schema.
        output_format: Target format. Allowed: 'csv', 'xlsx', 'pdf'.
        encoding: Text encoding for the output file (default: 'utf-8').
        metadata: Optional dictionary for format-specific options (keys: 'csv', 'xlsx', 'pdf').
    """

    columns: list[ColumnSpec]
    output_format: OutputFormat = "csv"
    encoding: str = "utf-8"
    metadata: dict[str, Any] = field(default_factory=dict)
    labels: list[str] = field(init=False)

    def __post_init__(self) -> None:
        # Cache labels once to avoid list comprehension on every access
        object.__setattr__(self, "labels", [col.label for col in self.columns])


class DBCursor(Protocol):
    """Minimal DB-API 2.0 cursor — only what SqlAdapter consumes."""

    @property
    def description(self) -> tuple[tuple[str, ...], ...] | None: ...

    def __iter__(self) -> Iterator[tuple[Any, ...]]: ...

    def execute(
        self,
        query: str,
        parameters: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> Any: ...

    def close(self) -> None: ...


class DBConnection(Protocol):
    """Minimal DB-API 2.0 connection — cursor() pattern per PEP 249."""

    def cursor(self) -> DBCursor: ...


class InputAdapter(Protocol):
    def adapt(self, data_source: Any) -> Iterable[Record]:
        """Normalize a data source to an iterable of mapping records."""


class Renderer(Protocol):
    def render(
        self,
        rows: Iterable[Mapping[str, Any]],
        spec: ReportSpec,
        destination: str | Path,
    ) -> Path:
        """Render normalized rows to a destination path."""
