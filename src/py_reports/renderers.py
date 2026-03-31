from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Mapping

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from rustpy_xlsxwriter import write_worksheet

from .contracts import OutputFormat, Renderer, ReportSpec
from .csv_options import CsvRenderOptions
from .xlsx_options import XlsxColumnOptions, XlsxRenderOptions


class CsvRenderer(Renderer):
    def render(
        self,
        rows: Iterable[Mapping[str, Any]],
        spec: ReportSpec,
        destination: str | Path,
    ) -> Path:
        output_path = Path(destination)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        options = CsvRenderOptions.from_metadata(spec.metadata)
        fieldnames = [column.label for column in spec.columns]
        with output_path.open("w", newline="", encoding=spec.encoding) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
                delimiter=options.delimiter,
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
        output_path = Path(destination)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        materialized_rows = list(rows)
        labels = [column.label for column in spec.columns]
        normalized_rows = [
            {label: row.get(label) for label in labels} for row in materialized_rows
        ]

        options = XlsxRenderOptions.from_metadata(spec.metadata)
        write_worksheet(normalized_rows, str(output_path), sheet_name=options.sheet_name)
        _apply_column_widths(output_path, labels, normalized_rows, options)
        return output_path


class PdfRenderer(Renderer):
    def render(
        self,
        rows: Iterable[Mapping[str, Any]],
        spec: ReportSpec,
        destination: str | Path,
    ) -> Path:
        output_path = Path(destination)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        labels = [column.label for column in spec.columns]
        materialized_rows = list(rows)

        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=landscape(A4),
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )

        header_row = [Paragraph(f"<b>{label}</b>", styles["Normal"]) for label in labels]
        data_rows = [
            [str("" if row.get(label) is None else row.get(label)) for label in labels]
            for row in materialized_rows
        ]
        table_data = [header_row, *data_rows]

        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        doc.build([table, Spacer(1, 0.5 * cm)])
        return output_path


def default_renderer_registry() -> dict[OutputFormat, Renderer]:
    return {"csv": CsvRenderer(), "xlsx": XlsxRenderer(), "pdf": PdfRenderer()}


def _apply_column_widths(
    output_path: Path,
    labels: list[str],
    normalized_rows: list[dict[str, Any]],
    options: XlsxRenderOptions,
) -> None:
    workbook = load_workbook(output_path)
    worksheet = workbook[options.sheet_name]

    for index, label in enumerate(labels, start=1):
        values = [row.get(label) for row in normalized_rows]
        width = _resolve_width_for_label(label=label, values=values, options=options)
        worksheet.column_dimensions[get_column_letter(index)].width = width

    workbook.save(output_path)


def _resolve_width_for_label(
    *, label: str, values: list[Any], options: XlsxRenderOptions
) -> float:
    column_options = options.columns.get(label, XlsxColumnOptions())
    explicit = column_options.width

    if explicit is not None:
        width = explicit
    elif options.width_mode in {"auto", "mixed"}:
        max_len = max(
            [len(label), *(len("" if value is None else str(value)) for value in values)]
        )
        width = float(max_len) + options.auto_padding
    else:
        width = options.default_width

    if column_options.min_width is not None:
        width = max(width, column_options.min_width)
    if column_options.max_width is not None:
        width = min(width, column_options.max_width)

    return width
