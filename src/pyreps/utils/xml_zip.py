from __future__ import annotations

import re
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import IO, Callable

from ..exceptions import RenderError

# Pre-compile common regexes for performance
_PATCH_SEARCH_OVERLAP = 128


def patch_zip_xml(
    src: Path,
    dst: Path,
    target_path: str,
    patcher_func: Callable[[IO[bytes], IO[bytes]], None],
) -> None:
    """
    Read source ZIP and write to destination, patching a specific XML file in transit.
    Non-target files are copied efficiently.
    """
    with (
        zipfile.ZipFile(src, "r") as reader,
        zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as writer,
    ):
        for item in reader.infolist():
            with reader.open(item) as in_file, writer.open(item, "w") as out_file:
                if item.filename == target_path:
                    patcher_func(in_file, out_file)
                else:
                    # Optimization: Use a larger buffer (1MB) to reduce syscalls.
                    shutil.copyfileobj(in_file, out_file, length=1024 * 1024)


def stream_regex_patch(
    instream: IO[bytes],
    outstream: IO[bytes],
    search_re: re.Pattern[bytes],
    insert_bytes: bytes,
    cleanup_re: re.Pattern[bytes] | None = None,
    max_metadata_size: int = 5 * 1024 * 1024,
) -> None:
    """
    Stream a file and insert/replace content at a regex match point.
    Uses memoryview and chunked buffering to keep memory usage low.
    """
    buffer = bytearray()
    chunk_size = 65536  # 64KB

    while True:
        chunk = instream.read(chunk_size)
        if not chunk:
            raise RenderError(f"Patch failed: {search_re.pattern!r} tag not found.")

        buffer.extend(chunk)

        if len(buffer) > max_metadata_size:
            raise RenderError(
                f"Patch failed: metadata exceeds {max_metadata_size // 1024 // 1024}MB limit."
            )

        # Search with overlap to handle matches split across chunks
        search_start = max(0, len(buffer) - len(chunk) - _PATCH_SEARCH_OVERLAP)
        match = search_re.search(buffer, search_start)
        if not match:
            continue

        split_idx = match.start()
        view = memoryview(buffer)
        head = view[:split_idx]
        tail = view[split_idx:]

        clean_head = head.tobytes()
        if cleanup_re:
            clean_head = cleanup_re.sub(b"", clean_head)

        outstream.write(clean_head)
        outstream.write(insert_bytes)
        outstream.write(tail)
        break

    shutil.copyfileobj(instream, outstream)


# Re-expose specifically for tests or internal use if needed, but keeping it generic is better.
# However, the test test_xlsx_stream_patch_tag_boundary expects a very specific function.
# Let's add it back as a convenience wrapper if it helps compatibility.

_SHEET_DATA_RE = re.compile(b"<[^:>]*:?sheetData")
_COLS_CLEAN_RE = re.compile(
    b"<[^:>]*:?cols[^>]*?(/>|.*?</[^:>]*:?cols>)", flags=re.DOTALL
)


def stream_patch_sheet_xml(
    instream: IO[bytes], outstream: IO[bytes], cols_el: ET.Element
) -> None:
    """Legacy/Compatibility wrapper for patching sheet XML."""
    cols_bytes = ET.tostring(cols_el, encoding="UTF-8")
    stream_regex_patch(
        instream, outstream, _SHEET_DATA_RE, cols_bytes, cleanup_re=_COLS_CLEAN_RE
    )
