from __future__ import annotations

import csv
import shutil
import zipfile
from pathlib import Path
from typing import Any, Iterable, Mapping

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

        labels = [column.label for column in spec.columns]
        options = XlsxRenderOptions.from_metadata(spec.metadata)

        tracker = _WidthTracker(rows, labels)
        write_worksheet(tracker, str(output_path), sheet_name=options.sheet_name)
        _apply_column_widths(output_path, labels, tracker.max_lens, options)
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

        data_rows: list[list[str]] = []
        paragraph_rows: list[list[Paragraph]] = []
        for row in rows:
            str_cells = [
                str("" if row.get(label) is None else row.get(label))
                for label in labels
            ]
            data_rows.append(str_cells)
            paragraph_rows.append(
                [Paragraph(cell, styles["Normal"]) for cell in str_cells]
            )

        table_data = [header_row, *paragraph_rows]

        col_widths = _resolve_pdf_column_widths(labels, data_rows, doc.width)
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
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


class _WidthTracker:
    """Generator wrapper that tracks max string length per column while streaming rows."""

    __slots__ = ("_rows", "_labels", "max_lens")

    def __init__(self, rows: Iterable[Mapping[str, Any]], labels: list[str]) -> None:
        self._rows = rows
        self._labels = labels
        self.max_lens: dict[str, int] = {label: len(label) for label in labels}

    def __iter__(self):
        for row in self._rows:
            normalized: dict[str, Any] = {}
            for label in self._labels:
                value = row.get(label)
                normalized[label] = value
                if value is not None:
                    self.max_lens[label] = max(
                        self.max_lens[label], len(str(value))
                    )
            yield normalized


def _apply_column_widths(
    output_path: Path,
    labels: list[str],
    max_lens: dict[str, int],
    options: XlsxRenderOptions,
) -> None:
    """Patch column widths in XLSX via streaming ZIP — constant memory."""
    widths = [
        _resolve_width_for_label(
            label=label, max_len=max_lens.get(label, len(label)), options=options
        )
        for label in labels
    ]

    cols_parts = ['<cols xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">']
    for i, w in enumerate(widths, start=1):
        cols_parts.append(
            f'<col min="{i}" max="{i}" width="{w:.2f}" customWidth="1"/>'
        )
    cols_parts.append("</cols>")
    cols_xml = "".join(cols_parts).encode("utf-8")

    sheet_path = "xl/worksheets/sheet1.xml"
    tmp_path = output_path.with_suffix(".tmp.xlsx")

    with zipfile.ZipFile(output_path, "r") as zin, \
         zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == sheet_path:
                with zin.open(item.filename) as src, zout.open(item.filename, "w") as dst:
                    _stream_inject_cols(src, dst, cols_xml)
            else:
                zout.writestr(item, zin.read(item.filename))

    shutil.move(str(tmp_path), str(output_path))


_CHUNK_SIZE = 65_536
_MARKER = b"<sheetData"


def _stream_inject_cols(
    src, dst, cols_xml: bytes
) -> None:
    """Stream sheet XML from *src* to *dst*, injecting *cols_xml* before <sheetData>."""
    buf = b""
    injected = False

    while True:
        chunk = src.read(_CHUNK_SIZE)
        if not chunk:
            break

        if injected:
            dst.write(chunk)
            continue

        buf += chunk
        pos = buf.find(_MARKER)
        if pos != -1:
            dst.write(buf[:pos])
            dst.write(cols_xml)
            dst.write(buf[pos:])
            injected = True
            buf = b""
        elif len(buf) > len(_MARKER):
            safe = len(buf) - len(_MARKER)
            dst.write(buf[:safe])
            buf = buf[safe:]

    if not injected:
        dst.write(buf)


def _resolve_width_for_label(
    *, label: str, max_len: int, options: XlsxRenderOptions
) -> float:
    column_options = options.columns.get(label, XlsxColumnOptions())
    explicit = column_options.width

    if explicit is not None:
        width = explicit
    elif options.width_mode in {"auto", "mixed"}:
        width = float(max_len) + options.auto_padding
    else:
        width = options.default_width

    if column_options.min_width is not None:
        width = max(width, column_options.min_width)
    if column_options.max_width is not None:
        width = min(width, column_options.max_width)

    return width


def _resolve_pdf_column_widths(
    labels: list[str],
    data_rows: list[list[str]],
    available_width: float,
) -> list[float]:
    """Distribute available page width proportionally based on max content length per column.

    Content length is capped to avoid a single column monopolising the page.
    Each column also gets a minimum width to ensure padding fits.
    """
    if not labels:
        return []

    _MAX_CHARS = 80
    _MIN_WIDTH_PT = 30.0  # enough to hold padding (8+8) plus a few characters

    char_widths = []
    for i, label in enumerate(labels):
        max_chars = len(label)
        for row in data_rows:
            if i < len(row):
                max_chars = max(max_chars, len(row[i]))
        char_widths.append(min(max(max_chars, 1), _MAX_CHARS))

    total_chars = sum(char_widths)
    widths = [available_width * (w / total_chars) for w in char_widths]

    # enforce minimum; redistribute surplus proportionally
    deficit = sum(max(0.0, _MIN_WIDTH_PT - w) for w in widths)
    if deficit > 0:
        surplus_indices = [i for i, w in enumerate(widths) if w > _MIN_WIDTH_PT]
        surplus_total = sum(widths[i] - _MIN_WIDTH_PT for i in surplus_indices)
        for i, w in enumerate(widths):
            if w < _MIN_WIDTH_PT:
                widths[i] = _MIN_WIDTH_PT
            elif surplus_total > 0:
                share = (w - _MIN_WIDTH_PT) / surplus_total
                widths[i] = _MIN_WIDTH_PT + (w - _MIN_WIDTH_PT) - deficit * share

    return widths
