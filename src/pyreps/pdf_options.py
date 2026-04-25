from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .exceptions import ReportError
from .utils.options import coerce_int


@dataclass(slots=True, frozen=True)
class PdfRenderOptions:
    chunk_size: int = 200
    paragraph_threshold: int = 30

    @classmethod
    def from_metadata(cls, metadata: Mapping[str, Any]) -> PdfRenderOptions:
        raw_pdf = metadata.get("pdf", {})
        if not isinstance(raw_pdf, Mapping):
            raise ReportError("metadata['pdf'] must be a mapping")
        return cls(
            chunk_size=coerce_int(
                raw_pdf.get("chunk_size", 200),
                field_name="metadata['pdf']['chunk_size']",
                min_value=1,
            ),
            paragraph_threshold=coerce_int(
                raw_pdf.get("paragraph_threshold", 30),
                field_name="metadata['pdf']['paragraph_threshold']",
                min_value=0,
            ),
        )
