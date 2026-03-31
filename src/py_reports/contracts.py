from __future__ import annotations

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
