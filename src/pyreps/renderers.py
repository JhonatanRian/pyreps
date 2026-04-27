from __future__ import annotations

import csv
import itertools
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping, Sequence
from operator import itemgetter
from pathlib import Path
from typing import Any, override, cast

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Frame,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from rustpy_xlsxwriter import FastExcel

from .contracts import OutputFormat, ProgressContext, Record, Renderer, ReportSpec
from .csv_options import CsvRenderOptions
from .exceptions import wrap_render_error
from .pdf_options import PdfRenderOptions
from .xlsx_options import XlsxColumnOptions, XlsxRenderOptions
from .utils import atomic_write
from .utils.files import is_remote_path, local_render_path, open_destination, prepare_destination
from .utils.options import clamp
from .utils.records import WidthTracker, get_cell_value
from .utils.xml_zip import patch_zip_xml, stream_patch_sheet_xml

# Common colors and style constants
_PDF_STRIPE_COLOR = colors.HexColor("#F1F5F9")
_PDF_HEADER_BLUE = colors.HexColor("#2563EB")
_PDF_GRID_COLOR = colors.HexColor("#CBD5E1")

XLSX_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
ET.register_namespace("", XLSX_NS)

_PDF_MAX_CHARS = 80
_PDF_MIN_WIDTH_PT = 30.0


class CsvRenderer(Renderer):
    @override
    @wrap_render_error("CSV")
    def render(
        self,
        rows: Iterable[Record],
        spec: ReportSpec,
        destination: str | Path,
        progress_context: ProgressContext,
    ) -> Path | str:
        output_path = prepare_destination(destination)
        options = CsvRenderOptions.from_metadata(spec.metadata)

        progress_context.set_stage("writing_rows")

        with open_destination(
            output_path, "w", newline="", encoding=spec.encoding
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=spec.labels,
                delimiter=options.delimiter,
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(progress_context.track_rows(rows))

        progress_context.set_stage("finalizing")

        return output_path


class XlsxRenderer(Renderer):
    @override
    @wrap_render_error("XLSX")
    def render(
        self,
        rows: Iterable[Record],
        spec: ReportSpec,
        destination: str | Path,
        progress_context: ProgressContext,
    ) -> Path | str:
        with local_render_path(
            destination, suffix=".xlsx", progress_context=progress_context
        ) as output_path:
            self._render_xlsx(rows, spec, output_path, progress_context)

        if not is_remote_path(destination):
            progress_context.set_stage("finalizing")

        return destination

    def _render_xlsx(
        self,
        rows: Iterable[Record],
        spec: ReportSpec,
        output_path: Path,
        progress_context: ProgressContext,
    ) -> None:
        """Core XLSX rendering logic."""
        options = XlsxRenderOptions.from_metadata(spec.metadata)
        progress_context.set_stage("writing_rows")

        if _needs_width_override(options):
            data, tracker = _get_xlsx_row_stream(rows, spec, options)
            FastExcel(str(output_path), autofit=False).sheet(
                options.sheet_name,
                progress_context.track_rows(data),
            ).save()

            progress_context.set_stage("patching_column_widths")

            _stream_patch_column_widths(
                output_path,
                spec.labels,
                tracker.max_lens if tracker else {},
                options,
            )
        else:
            use_autofit = options.width_mode != "manual"
            FastExcel(str(output_path), autofit=use_autofit).sheet(
                options.sheet_name,
                progress_context.track_rows(rows),
            ).save()


def _get_xlsx_row_stream(
    rows: Iterable[Mapping[str, Any]],
    spec: ReportSpec,
    options: XlsxRenderOptions,
) -> tuple[Iterable[Mapping[str, Any]], WidthTracker | None]:
    """Determine the optimal row stream and tracker instance for XLSX rendering."""
    if options.width_mode not in {"auto", "mixed"}:
        return rows, None

    exclude = {
        label for label, col in (options.columns or {}).items() if col.width is not None
    }

    tracked_labels = [label for label in spec.labels if label not in exclude]
    if not tracked_labels:
        return rows, None

    tracker = WidthTracker(rows, spec.labels, exclude_labels=exclude)
    return tracker, tracker


# Common style commands to avoid duplication
_PDF_COMMON_STYLE = [
    ("GRID", (0, 0), (-1, -1), 0.5, _PDF_GRID_COLOR),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
]


class StreamingDocTemplate(SimpleDocTemplate):
    """DocTemplate that handles flowables from a generator to avoid memory bottlenecks."""

    def build_from_generator(self, flowables_generator: Iterable[Any]) -> None:
        self._calc()  # type: ignore
        self._startBuild(self.filename)  # type: ignore
        self.canv._doctemplate = self  # type: ignore

        for flowable in flowables_generator:
            f_list = [flowable]
            while f_list:
                self.clean_hanging()
                self.handle_flowable(f_list)

        self._endBuild()  # type: ignore


class PdfRenderer(Renderer):
    @override
    @wrap_render_error("PDF")
    def render(
        self,
        rows: Iterable[Record],
        spec: ReportSpec,
        destination: str | Path,
        progress_context: ProgressContext,
    ) -> Path | str:
        with local_render_path(
            destination, suffix=".pdf", progress_context=progress_context
        ) as output_path:
            self._render_pdf(rows, spec, output_path, progress_context)

        if not is_remote_path(destination):
            progress_context.set_stage("finalizing")

        return destination

    def _render_pdf(
        self,
        rows: Iterable[Record],
        spec: ReportSpec,
        output_path: Path,
        progress_context: ProgressContext,
    ) -> None:
        """Core PDF rendering logic using ReportLab Platypus."""
        labels = spec.labels
        styles = getSampleStyleSheet()
        normal_style = cast(ParagraphStyle, styles["Normal"])

        progress_context.set_stage("preparing")

        doc = StreamingDocTemplate(
            str(output_path),
            pagesize=landscape(A4),
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )

        row_iter = iter(rows)
        sample = list(itertools.islice(row_iter, 100))
        all_rows_iter = itertools.chain(sample, row_iter)

        sample_data = [
            [get_cell_value(row, label) for label in labels] for row in sample
        ]
        col_widths = _resolve_pdf_column_widths(labels, sample_data, doc.width)

        header_table = self._create_header_table(labels, col_widths, normal_style)
        _, header_height = header_table.wrap(doc.width, doc.height)

        self._setup_pages(doc, header_table, header_height)

        pdf_opts = PdfRenderOptions.from_metadata(spec.metadata)
        style_even, style_odd = self._get_table_styles()

        def generate_chunks() -> Iterable[Table | Spacer]:
            threshold = pdf_opts.paragraph_threshold
            fetcher = itemgetter(*labels)
            single_label = len(labels) == 1
            is_even = True

            progress_context.set_stage("writing_rows")
            rows_to_track = progress_context.track_rows(all_rows_iter)

            for chunk in itertools.batched(rows_to_track, pdf_opts.chunk_size):
                table_rows = []
                for row in chunk:
                    values = fetcher(row)
                    if single_label:
                        values = (values,)

                    row_data = []
                    for val in values:
                        v_str = str(val) if val is not None else ""
                        if len(v_str) > threshold or "\n" in v_str:
                            row_data.append(Paragraph(v_str, normal_style))
                        else:
                            row_data.append(v_str)
                    table_rows.append(row_data)

                table = Table(table_rows, colWidths=col_widths)
                table.setStyle(style_even if is_even else style_odd)
                is_even = not is_even
                yield table

            yield Spacer(1, 0.5 * cm)

        doc.build_from_generator(generate_chunks())

    def _get_table_styles(self) -> tuple[TableStyle, TableStyle]:
        """Create alternating row styles for PDF tables."""
        base_style_cmds = _PDF_COMMON_STYLE + [
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]

        style_even = TableStyle(
            base_style_cmds
            + [("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _PDF_STRIPE_COLOR])]
        )
        style_odd = TableStyle(
            base_style_cmds
            + [("ROWBACKGROUNDS", (0, 0), (-1, -1), [_PDF_STRIPE_COLOR, colors.white])]
        )
        return style_even, style_odd

    def _create_header_table(
        self, labels: Sequence[str], col_widths: Sequence[float], style: ParagraphStyle
    ) -> Table:
        header_table = Table(
            [[Paragraph(f"<b>{label}</b>", style) for label in labels]],
            colWidths=col_widths,  # type: ignore[arg-type]
        )
        header_table.setStyle(
            TableStyle(
                _PDF_COMMON_STYLE
                + [
                    ("BACKGROUND", (0, 0), (-1, 0), _PDF_HEADER_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                ]
            )
        )
        return header_table

    def _setup_pages(
        self, doc: StreamingDocTemplate, header_table: Table, header_height: float
    ) -> None:
        def draw_header(
            canv: canvas.Canvas, doc_template: StreamingDocTemplate
        ) -> None:
            header_table.canv = canv
            header_table.drawOn(
                canv,
                doc_template.leftMargin,
                doc_template.height + doc_template.bottomMargin - header_height,
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


def default_renderer_registry() -> dict[OutputFormat, Renderer]:
    return {"csv": CsvRenderer(), "xlsx": XlsxRenderer(), "pdf": PdfRenderer()}


def _needs_width_override(options: XlsxRenderOptions) -> bool:
    """Return True when per-column width overrides require DOM patching."""
    return options.width_mode == "manual" or bool(options.columns)


def _build_cols_element(
    labels: Sequence[str],
    max_lens: dict[str, int],
    options: XlsxRenderOptions,
) -> ET.Element:
    """Build a <cols> XML element from resolved widths."""
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
_SHEET_DATA_RE = re.compile(b"<[^:>]*:?sheetData")
_COLS_CLEAN_RE = re.compile(
    b"<[^:>]*:?cols[^>]*?(/>|.*?</[^:>]*:?cols>)", flags=re.DOTALL
)


def _stream_patch_column_widths(
    output_path: Path,
    labels: Sequence[str],
    max_lens: dict[str, int],
    options: XlsxRenderOptions,
) -> None:
    """Patch column widths in XLSX using streaming."""
    cols_el = _build_cols_element(labels, max_lens, options)

    def patcher(instream: Any, outstream: Any) -> None:
        stream_patch_sheet_xml(instream, outstream, cols_el)

    with atomic_write(output_path) as tmp_path:
        patch_zip_xml(output_path, tmp_path, _SHEET_PATH, patcher)


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

    return clamp(
        width,
        column_options.min_width or 0.0,
        column_options.max_width or float("inf"),
    )


def _resolve_pdf_column_widths(
    labels: Sequence[str],
    data_rows: list[list[str]],
    available_width: float,
) -> tuple[float, ...]:
    """Distribute available page width proportionally based on max content length per column."""
    if not labels:
        return ()

    max_content_lens = [len(label) for label in labels]
    if data_rows:
        for i, col_data in enumerate(zip(*data_rows)):
            max_content_lens[i] = max(max_content_lens[i], max(map(len, col_data)))

    max_content_lens = [clamp(w, 1, _PDF_MAX_CHARS) for w in max_content_lens]

    total_chars = sum(max_content_lens)
    widths = [available_width * (w / total_chars) for w in max_content_lens]

    deficit = sum(max(0.0, _PDF_MIN_WIDTH_PT - w) for w in widths)
    if deficit <= 0:
        return tuple(widths)

    surplus_total = sum(max(0.0, w - _PDF_MIN_WIDTH_PT) for w in widths)
    ratio = min(deficit / surplus_total, 1.0) if surplus_total > 0 else 0.0

    return tuple(
        _PDF_MIN_WIDTH_PT
        if w < _PDF_MIN_WIDTH_PT
        else w - (w - _PDF_MIN_WIDTH_PT) * ratio
        for w in widths
    )
