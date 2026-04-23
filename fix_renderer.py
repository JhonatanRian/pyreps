import re
from pathlib import Path

path = Path("src/py_reports/renderers.py")
content = path.read_text()

# 1. Rename _dom_patch_column_widths to _stream_patch_column_widths in definition
content = content.replace("def _dom_patch_column_widths(", "def _stream_patch_column_widths(")
content = content.replace("with zin.open(item) as fin, zout.open(item, \"w\") as fout:", "with zin.open(item) as in_file, zout.open(item, \"w\") as out_file:")
content = content.replace("_stream_patch_sheet_xml(fin, fout, cols_el)", "_stream_patch_sheet_xml(in_file, out_file, cols_el)")
content = content.replace("shutil.copyfileobj(fin, fout)", "shutil.copyfileobj(in_file, out_file)")

# 2. Fix the regex and the streaming logic
# The issue might be that ET.tostring(cols_el) includes xmlns which might conflict or be poorly handled.
# Also, we should ensure we don't include the XML declaration in cols_bytes.

old_stream_patch_all = '''_SHEET_DATA_RE = re.compile(b"<[^:>]*:?sheetData")
_COLS_CLEAN_RE = re.compile(b"<[^:>]*:?cols.*?(/>|</[^:>]*:?cols>)", flags=re.DOTALL)


def _stream_patch_sheet_xml(
    instream: IO[bytes], outstream: IO[bytes], cols_el: ET.Element
) -> None:
    """Stream sheet XML, insert/replace <cols> before <sheetData> using a chunked buffer."""
    cols_bytes = ET.tostring(cols_el, encoding="UTF-8")

    buffer = bytearray()
    chunk_size = 65536  # 64KB
    max_buffer_size = 5 * 1024 * 1024  # 5MB safety limit

    while True:
        chunk = instream.read(chunk_size)
        if not chunk:
            # Fallback: '<sheetData' tag not found. Append at the end.
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
            continue  # Need to read more chunks

        # Breakpoint found. Split the file before insertion.
        split_idx = match.start()
        head = bytes(buffer[:split_idx])
        tail = bytes(buffer[split_idx:])

        # Prevent duplicate <cols> blocks by strictly cleaning the previous section.
        clean_head = _COLS_CLEAN_RE.sub(b"", head)

        # Write sections in the correct order required by XLSX
        outstream.write(clean_head)
        outstream.write(cols_bytes)
        outstream.write(tail)
        break  # Exit loop to start streaming the remainder

    # Efficiently transfer the rest of the file (if any)
    shutil.copyfileobj(instream, outstream)'''

# I'll use a safer approach for XML patching that avoids namespace issues if possible.
# Actually, the error "mismatched tag" is very specific.
# If head = b"<worksheet><cols>" and we remove <cols>, we get b"<worksheet>".
# Then we add new <cols>, we get b"<worksheet><cols>".
# Then we add tail which is b"<sheetData>...</worksheet>".
# Total: b"<worksheet><cols><sheetData>...</worksheet>". This is valid.

# WAIT! I know what happened! 
# ET.tostring(cols_el) with ET.register_namespace("", XLSX_NS) might be producing:
# b'<cols xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">...</cols>'
# But if the worksheet already has this xmlns, it's fine.

# Let's check if cols_bytes has a prefix.
# I'll use a more robust regex that doesn't care about prefixes in _COLS_CLEAN_RE.
# The current one is b"<[^:>]*:?cols.*?(/>|</[^:>]*:?cols>)".

new_stream_patch_all = '''# Pre-compile regexes for performance and robustness
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
    shutil.copyfileobj(instream, outstream)'''

content = content.replace(old_stream_patch_all, new_stream_patch_all)

path.write_text(content)
print("Fix applied.")
