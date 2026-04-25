from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .exceptions import ReportError


@dataclass(slots=True, frozen=True)
class CsvRenderOptions:
    delimiter: str = ","

    def __post_init__(self) -> None:
        if not isinstance(self.delimiter, str) or len(self.delimiter) != 1:
            raise ReportError("metadata['csv']['delimiter'] must be a single character")

    @classmethod
    def from_metadata(cls, metadata: Mapping[str, Any]) -> CsvRenderOptions:
        raw_csv = metadata.get("csv", {})
        if not isinstance(raw_csv, Mapping):
            raise ReportError("metadata['csv'] must be a mapping")
        return cls(delimiter=raw_csv.get("delimiter", ","))
