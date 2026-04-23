from __future__ import annotations

import csv
import functools
import itertools
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterable, Iterator, Mapping
from operator import itemgetter
from pathlib import Path
from typing import IO, Any, Callable, TypeVar

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

from .contracts import OutputFormat, Renderer, ReportSpec
from .csv_options import CsvRenderOptions
from .exceptions import RenderError
from .pdf_options import PdfRenderOptions
from .xlsx_options import XlsxColumnOptions, XlsxRenderOptions
from .utils import atomic_write
from .utils.options import clamp

# Common colors and style constants
_PDF_STRIPE_COLOR = colors.HexColor("#F1F5F9")
_PDF_HEADER_BLUE = colors.HexColor("#2563EB")
_PDF_GRID_COLOR = colors.HexColor("#CBD5E1")


XLSX_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
ET.register_namespace("", XLSX_NS)

_PDF_MAX_CHARS = 80
_PDF_MIN_WIDTH_PT = 30.0  # enough to hold padding (8+8) plus a few characters


F = TypeVar("F", bound=Callable[..., Any])


def wrap_render_error(format_name: str) -> Callable[[F], F]:
    """Decorator to wrap any exception during rendering into a RenderError."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                raise RenderError(f"Failed to render {format_name}: {exc}") from exc

        return wrapper  # type: ignore

    return decorator


def _prepare_destination(destination: str | Path) -> Path:
    """Ensure parent directory exists and return Path object."""
    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


class CsvRenderer(Renderer):
    @wrap_render_error("CSV")
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
    @wrap_render_error("XLSX")
    def render(
        self,
        rows: Iterable[Mapping[str, Any]],
        spec: ReportSpec,
        destination: str | Path,
    ) -> Path:
        output_path = _prepare_destination(destination)
        options = XlsxRenderOptions.from_metadata(spec.metadata)

        needs_override = _needs_width_override(options)

        if needs_override:
            data, tracker = _get_xlsx_row_stream(rows, spec, options)
            FastExcel(str(output_path), autofit=False).sheet(
                options.sheet_name, data
            ).save()
            _stream_patch_column_widths(
                output_path, spec.labels,
                tracker.max_lens if tracker else {},
                options,
            )
        else:
            # Pure autofit — let Rust handle everything, no post-processing.
            use_autofit = options.width_mode != "manual"
            FastExcel(str(output_path), autofit=use_autofit).sheet(
                options.sheet_name, rows
            ).save()

        return output_path


def _get_xlsx_row_stream(
    rows: Iterable[Mapping[str, Any]],
    spec: ReportSpec,
    options: XlsxRenderOptions,
) -> tuple[Iterable[Mapping[str, Any]], _WidthTracker | None]:
    """Determine the optimal row stream and tracker instance for XLSX rendering."""
    if options.width_mode not in {"auto", "mixed"}:
        return rows, None

    exclude = {
        label for label, col in (options.columns or {}).items()
        if col.width is not None
    }

    # Only instantiate tracker if there are columns in the current report that need auto-width.
    tracked_labels = [label for label in spec.labels if label not in exclude]

    if not tracked_labels:
        return rows, None

    tracker = _WidthTracker(rows, spec.labels, exclude_labels=exclude)
    return tracker, tracker


# Common style commands to avoid duplication between header and body
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
    @wrap_render_error("PDF")
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
        pdf_opts = PdfRenderOptions.from_metadata(spec.metadata)
        chunk_size = pdf_opts.chunk_size

        base_style_cmds = _PDF_COMMON_STYLE + [
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]

        # Pre-instantiate TableStyles to avoid allocation in generator loop
        style_even = TableStyle(
            base_style_cmds + [("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _PDF_STRIPE_COLOR])]
        )
        style_odd = TableStyle(
            base_style_cmds + [("ROWBACKGROUNDS", (0, 0), (-1, -1), [_PDF_STRIPE_COLOR, colors.white])]
        )

        def generate_chunks() -> Iterable[Table | Spacer]:
            # Pre-bind variables and function references for performance
            threshold = pdf_opts.paragraph_threshold
            _len, _str, _Paragraph = len, str, Paragraph
            fetcher = itemgetter(*labels)
            
            # For a single label, itemgetter returns a scalar, otherwise a tuple.
            single_label = len(labels) == 1
            is_even = True
            
            while True:
                chunk = list(itertools.islice(all_rows_iter, chunk_size))
                if not chunk:
                    break

                table_rows = []
                for row in chunk:
                    # Multi-field retrieval in C
                    values = fetcher(row)
                    if single_label:
                        values = (values,)
                        
                    row_data = []
                    for val in values:
                        v_str = _str(val) if val is not None else ""
                        if _len(v_str) > threshold or "\n" in v_str:
                            row_data.append(_Paragraph(v_str, normal_style))
                        else:
                            row_data.append(v_str)
                    table_rows.append(row_data)

                table = Table(table_rows, colWidths=col_widths)
                table.setStyle(style_even if is_even else style_odd)
                is_even = not is_even

                yield table

            yield Spacer(1, 0.5 * cm)

        doc.build_from_generator(generate_chunks())
        return output_path

    def _create_header_table(self, labels: list[str], col_widths: list[float], style: ParagraphStyle) -> Table:
        header_table = Table(
            [[Paragraph(f"<b>{label}</b>", style) for label in labels]],
            colWidths=col_widths,
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

    def _setup_pages(self, doc: StreamingDocTemplate, header_table: Table, header_height: float) -> None:
        def draw_header(canv: canvas.Canvas, doc_template: StreamingDocTemplate) -> None:
            header_table.canv = canv
            header_table.drawOn(
                canv, doc_template.leftMargin, doc_template.height + doc_template.bottomMargin - header_height
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

    def __init__(
        self,
        rows: Iterable[Mapping[str, Any]],
        labels: list[str],
        exclude_labels: set[str] | None = None,
    ) -> None:
        self._rows = rows
        # Filter labels to only track those that need auto-width.
        exclude = exclude_labels or set()
        self._labels = [label for label in labels if label not in exclude]
        self.max_lens: dict[str, int] = {label: len(label) for label in labels}

    def __iter__(self) -> Iterator[Mapping[str, Any]]:
        # Local variable access is faster than attribute access in tight loops.
        labels = self._labels
        if not labels:
            yield from self._rows
            return

        # Optimization: Move built-ins and indexing overhead out of the hot loop.
        fetcher = itemgetter(*labels)
        indices = list(range(len(labels)))
        current_max_lens = [self.max_lens[label] for label in labels]
        _len, _type, _str, _str_type = len, type, str, str

        for row in self._rows:
            # itemgetter(*labels)(row) is faster than individual row[label] lookups.
            # It returns a single value if len(labels) == 1, else a tuple.
            values = fetcher(row)
            if _len(labels) == 1:
                values = (values,)

            for i in indices:
                val = values[i]
                if val is None:
                    continue

                # Avoid str() if already a string; type() check is faster.
                val_len = _len(val) if _type(val) is _str_type else _len(_str(val))
                if val_len > current_max_lens[i]:
                    current_max_lens[i] = val_len
            yield row

        # Synchronize back to the dictionary for use in patching.
        self.max_lens.update(zip(labels, current_max_lens))


def _needs_width_override(options: XlsxRenderOptions) -> bool:
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


def _stream_patch_column_widths(
    output_path: Path,
    labels: list[str],
    max_lens: dict[str, int],
    options: XlsxRenderOptions,
) -> None:
    """Patch column widths in XLSX using streaming — memory efficient."""
    cols_el = _build_cols_element(labels, max_lens, options)

    with atomic_write(output_path) as tmp_path:
        _rebuild_xlsx_archive(output_path, tmp_path, cols_el)


def _rebuild_xlsx_archive(src: Path, dst: Path, cols_el: ET.Element) -> None:
    """Read source XLSX and write to destination, patching the worksheet XML in transit."""
    with zipfile.ZipFile(src, "r") as reader, zipfile.ZipFile(
        dst, "w", compression=zipfile.ZIP_DEFLATED
    ) as writer:
        for item in reader.infolist():
            with reader.open(item) as in_file, writer.open(item, "w") as out_file:
                if item.filename == _SHEET_PATH:
                    _stream_patch_sheet_xml(in_file, out_file, cols_el)
                else:
                    # Optimization: Use a larger buffer (1MB) to reduce syscalls.
                    shutil.copyfileobj(in_file, out_file, length=1024 * 1024)


# Pre-compile regexes for performance and robustness
_SHEET_DATA_RE = re.compile(b"<[^:>]*:?sheetData")
# Matches <cols> or <x:cols> with any attributes, including self-closing
_COLS_CLEAN_RE = re.compile(b"<[^:>]*:?cols[^>]*?(/>|.*?</[^:>]*:?cols>)", flags=re.DOTALL)


def _stream_patch_sheet_xml(
    instream: IO[bytes], outstream: IO[bytes], cols_el: ET.Element
) -> None:
    """Stream sheet XML, insert/replace <cols> before <sheetData> using a chunked buffer."""
    # Serialize the <cols> element. We don't want the XML declaration.
    cols_bytes = ET.tostring(cols_el, encoding="UTF-8")

    buffer = bytearray()
    chunk_size = 65536  # 64KB
    max_buffer_size = 5 * 1024 * 1024  # 5MB safety limit

    while True:
        chunk = instream.read(chunk_size)
        if not chunk:
            # Fallback: '<sheetData' tag not found. Append before end if possible.
            outstream.write(buffer)
            outstream.write(cols_bytes)
            return

        buffer.extend(chunk)

        if len(buffer) > max_buffer_size:
            # Safety limit to prevent OOM on malformed XML.
            outstream.write(buffer)
            outstream.write(cols_bytes)
            shutil.copyfileobj(instream, outstream)
            return

        # Look for the start of the main tag
        match = _SHEET_DATA_RE.search(buffer)
        if not match:
            continue

        # Breakpoint found. Split the file before insertion.
        split_idx = match.start()
        head = bytes(buffer[:split_idx])
        tail = bytes(buffer[split_idx:])

        # Clean any existing <cols> blocks from the head.
        clean_head = _COLS_CLEAN_RE.sub(b"", head)

        # Write sections in the correct order required by XLSX
        outstream.write(clean_head)
        outstream.write(cols_bytes)
        outstream.write(tail)
        break

    # Efficiently transfer the rest of the file.
    shutil.copyfileobj(instream, outstream)


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

    # 1. Get max length per column (header + sampling rows)
    max_content_lens = [len(label) for label in labels]
    if data_rows:
        for i, col_data in enumerate(zip(*data_rows)):
            max_content_lens[i] = max(max_content_lens[i], max(map(len, col_data)))

    # Clamp to reasonable bounds to avoid extreme proportions
    max_content_lens = [clamp(w, 1, _PDF_MAX_CHARS) for w in max_content_lens]

    # 2. Initial proportional distribution
    total_chars = sum(max_content_lens)
    widths = [available_width * (w / total_chars) for w in max_content_lens]

    # 3. Enforce minimum width by redistributing surplus from larger columns
    deficit = sum(max(0.0, _PDF_MIN_WIDTH_PT - w) for w in widths)
    if deficit <= 0:
        return widths

    surplus_total = sum(max(0.0, w - _PDF_MIN_WIDTH_PT) for w in widths)
    # Ratio of deficit to subtract from each column's surplus.
    # min(..., 1.0) ensures we never subtract more than the surplus itself.
    ratio = min(deficit / surplus_total, 1.0) if surplus_total > 0 else 0.0

    return [
        _PDF_MIN_WIDTH_PT if w < _PDF_MIN_WIDTH_PT
        else w - (w - _PDF_MIN_WIDTH_PT) * ratio
        for w in widths
    ]
