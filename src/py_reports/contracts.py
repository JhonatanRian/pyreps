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
    label: str
    source: str
    required: bool = False
    default: Any = None
    formatter: Formatter | None = None
    type: ColumnType | None = None


@dataclass(slots=True, frozen=True)
class ReportSpec:
    columns: list[ColumnSpec]
    output_format: OutputFormat = "csv"
    encoding: str = "utf-8"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def labels(self) -> list[str]:
        return [col.label for col in self.columns]


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
