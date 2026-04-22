from __future__ import annotations

import csv
import itertools
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from rustpy_xlsxwriter import FastExcel

from .contracts import OutputFormat, Renderer, ReportSpec
from .csv_options import CsvRenderOptions
from .xlsx_options import XlsxColumnOptions, XlsxRenderOptions


XLSX_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _prepare_destination(destination: str | Path) -> Path:
    """Ensure parent directory exists and return Path object."""
    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


class CsvRenderer(Renderer):
    def render(
        self,
        rows: Iterable[Mapping[str, Any]],
        spec: ReportSpec,
        destination: str | Path,
    ) -> Path:
        output_path = _prepare_destination(destination)
        options = CsvRenderOptions.from_metadata(spec.metadata)

        with output_path.open("w", newline="", encoding=spec.encoding) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=spec.labels,
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
        output_path = _prepare_destination(destination)
        options = XlsxRenderOptions.from_metadata(spec.metadata)

        needs_override = _needs_width_override(spec.labels, options)

        if needs_override:
            # Track widths manually for per-column overrides + DOM patch.
            tracker = _WidthTracker(rows, spec.labels)
            use_autofit = options.width_mode in {"auto", "mixed"}
            FastExcel(str(output_path), autofit=use_autofit).sheet(
                options.sheet_name, tracker
            ).save()
            _dom_patch_column_widths(
                output_path, spec.labels, tracker.max_lens, options
            )
        else:
            # Pure autofit — let Rust handle everything, no post-processing.
            use_autofit = options.width_mode != "manual"
            FastExcel(str(output_path), autofit=use_autofit).sheet(
                options.sheet_name, rows
            ).save()

        return output_path


# Common style commands to avoid duplication between header and body
_PDF_COMMON_STYLE = [
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
]


class StreamingDocTemplate(SimpleDocTemplate):
    """DocTemplate that handles flowables from a generator to avoid memory bottlenecks."""

    def build_from_generator(self, flowables_generator: Iterable[Any]) -> None:
        self._calc()
        self._startBuild(self.filename)
        self.canv._doctemplate = self

        for flowable in flowables_generator:
            f_list = [flowable]
            while f_list:
                self.clean_hanging()
                self.handle_flowable(f_list)

        self._endBuild()


class PdfRenderer(Renderer):
    def render(
        self,
        rows: Iterable[Mapping[str, Any]],
        spec: ReportSpec,
        destination: str | Path,
    ) -> Path:
        output_path = _prepare_destination(destination)
        labels = spec.labels
        styles = getSampleStyleSheet()
        normal_style = styles["Normal"]

        doc = StreamingDocTemplate(
            str(output_path),
            pagesize=landscape(A4),
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )

        # 1. Sample and Width Calculation
        row_iter = iter(rows)
        sample = list(itertools.islice(row_iter, 100))
        all_rows_iter = itertools.chain(sample, row_iter)

        sample_data = [
            [_get_cell_value(row, label) for label in labels] for row in sample
        ]
        col_widths = _resolve_pdf_column_widths(labels, sample_data, doc.width)

        # 2. Header Setup
        header_table = self._create_header_table(labels, col_widths, normal_style)
        _, header_height = header_table.wrap(doc.width, doc.height)

        # 3. Template and Frame Setup
        self._setup_pages(doc, header_table, header_height)

        # 4. Body Rendering
        body_style = TableStyle(
            _PDF_COMMON_STYLE
            + [
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )

        def generate_chunks() -> Iterable[Any]:
            chunk_size = 200
            while True:
                chunk = list(itertools.islice(all_rows_iter, chunk_size))
                if not chunk:
                    break

                table_rows = [
                    [Paragraph(_get_cell_value(row, label), normal_style) for label in labels]
                    for row in chunk
                ]
                table = Table(table_rows, colWidths=col_widths)
                table.setStyle(body_style)
                yield table

            yield Spacer(1, 0.5 * cm)

        doc.build_from_generator(generate_chunks())
        return output_path

    def _create_header_table(self, labels: list[str], col_widths: list[float], style) -> Table:
        header_table = Table(
            [[Paragraph(f"<b>{label}</b>", style) for label in labels]],
            colWidths=col_widths,
        )
        header_table.setStyle(
            TableStyle(
                _PDF_COMMON_STYLE
                + [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                ]
            )
        )
        return header_table

    def _setup_pages(self, doc: StreamingDocTemplate, header_table: Table, header_height: float):
        def draw_header(canvas: canvas.Canvas, doc: StreamingDocTemplate) -> None:
            header_table.canv = canvas
            header_table.drawOn(
                canvas, doc.leftMargin, doc.height + doc.bottomMargin - header_height
            )

        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height - header_height,
            id="normal",
        )
        doc.addPageTemplates(
            [
                PageTemplate(id="First", frames=[frame], onPage=draw_header),
                PageTemplate(id="Later", frames=[frame], onPage=draw_header),
            ]
        )


def _get_cell_value(row: Mapping[str, Any], label: str) -> str:
    val = row.get(label)
    return str(val) if val is not None else ""


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
            for label in self._labels:
                value = row.get(label)
                if value is not None:
                    # Avoid multiple str() calls
                    val_str = str(value)
                    self.max_lens[label] = max(self.max_lens[label], len(val_str))
            yield row


def _needs_width_override(labels: list[str], options: XlsxRenderOptions) -> bool:
    """Return True when per-column width overrides require DOM patching."""
    if options.width_mode == "manual":
        return True
    if options.columns:
        return True
    return False


def _build_cols_element(
    labels: list[str],
    max_lens: dict[str, int],
    options: XlsxRenderOptions,
) -> ET.Element:
    """Build a <cols> XML element from resolved widths."""
    ET.register_namespace("", XLSX_NS)
    cols_el = ET.Element(f"{{{XLSX_NS}}}cols")
    for i, label in enumerate(labels, start=1):
        width = _resolve_width_for_label(
            label=label, max_len=max_lens.get(label, len(label)), options=options
        )
        ET.SubElement(
            cols_el,
            f"{{{XLSX_NS}}}col",
            {"min": str(i), "max": str(i), "width": f"{width:.2f}", "customWidth": "1"},
        )
    return cols_el


_SHEET_PATH = "xl/worksheets/sheet1.xml"


def _dom_patch_column_widths(
    output_path: Path,
    labels: list[str],
    max_lens: dict[str, int],
    options: XlsxRenderOptions,
) -> None:
    """Patch column widths in XLSX using full DOM parsing — no regex."""
    cols_el = _build_cols_element(labels, max_lens, options)
    tmp_path = output_path.with_suffix(".tmp.xlsx")

    with zipfile.ZipFile(output_path, "r") as zin, zipfile.ZipFile(
        tmp_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            if item.filename == _SHEET_PATH:
                sheet_xml = zin.read(item.filename)
                patched = _patch_sheet_xml(sheet_xml, cols_el)
                zout.writestr(item, patched)
            else:
                zout.writestr(item, zin.read(item.filename))

    # Atomic replace: rename tmp over original.
    tmp_path.replace(output_path)


def _patch_sheet_xml(sheet_xml: bytes, cols_el: ET.Element) -> bytes:
    """Parse sheet XML, insert/replace <cols> before <sheetData>, return bytes."""
    ns = {"ns": XLSX_NS}
    root = ET.fromstring(sheet_xml)

    # Remove any existing <cols> element.
    for existing_cols in root.findall("ns:cols", ns):
        root.remove(existing_cols)

    # Find <sheetData> and insert <cols> right before it.
    sheet_data = root.find("ns:sheetData", ns)
    if sheet_data is not None:
        idx = list(root).index(sheet_data)
        root.insert(idx, cols_el)
    else:
        # Fallback: append at end (should not happen in valid XLSX).
        root.append(cols_el)

    ET.register_namespace("", XLSX_NS)
    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")


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
