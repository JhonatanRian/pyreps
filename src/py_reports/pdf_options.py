from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .exceptions import ReportError


@dataclass(slots=True, frozen=True)
class PdfRenderOptions:
    chunk_size: int = 200
    paragraph_threshold: int = 30

    def __post_init__(self) -> None:
        if not isinstance(self.chunk_size, int) or self.chunk_size <= 0:
            raise ReportError("metadata['pdf']['chunk_size'] must be a positive integer")

        if not isinstance(self.paragraph_threshold, int) or self.paragraph_threshold < 0:
            raise ReportError("metadata['pdf']['paragraph_threshold'] must be a non-negative integer")

    @classmethod
    def from_metadata(cls, metadata: Mapping[str, Any]) -> PdfRenderOptions:
        raw_pdf = metadata.get("pdf", {})
        if not isinstance(raw_pdf, Mapping):
            raise ReportError("metadata['pdf'] must be a mapping")
        return cls(
            chunk_size=raw_pdf.get("chunk_size", 200),
            paragraph_threshold=raw_pdf.get("paragraph_threshold", 30),
        )
