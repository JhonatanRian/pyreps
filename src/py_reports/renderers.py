from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Mapping

from .contracts import OutputFormat, Renderer, ReportSpec


class CsvRenderer(Renderer):
    def render(
        self,
        rows: Iterable[Mapping[str, Any]],
        spec: ReportSpec,
        destination: str | Path,
    ) -> Path:
        output_path = Path(destination)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [column.label for column in spec.columns]
        with output_path.open("w", newline="", encoding=spec.encoding) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
                delimiter=spec.delimiter,
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(rows)
        return output_path


class XlsxRenderer(Renderer):
    def render(
        self,
        rows: Iterable[Mapping[str, Any]],
        spec: ReportSpec,
        destination: str | Path,
    ) -> Path:
        raise NotImplementedError(
            "XLSX renderer is scaffolded but not implemented yet."
        )


class PdfRenderer(Renderer):
    def render(
        self,
        rows: Iterable[Mapping[str, Any]],
        spec: ReportSpec,
        destination: str | Path,
    ) -> Path:
        raise NotImplementedError("PDF renderer is scaffolded but not implemented yet.")


def default_renderer_registry() -> dict[OutputFormat, Renderer]:
    return {"csv": CsvRenderer(), "xlsx": XlsxRenderer(), "pdf": PdfRenderer()}
