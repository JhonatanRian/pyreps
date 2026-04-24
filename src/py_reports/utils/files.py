import contextlib
import tempfile
from collections.abc import Iterator
from pathlib import Path


@contextlib.contextmanager
def atomic_write(destination: Path | str, suffix: str | None = None) -> Iterator[Path]:
    """
    Composable context manager for atomic file writes.
    Yields a temporary Path object on the same filesystem.
    On success, atomically replaces the destination.
    On exception, cleans up the temporary file.
    """
    dest = Path(destination)
    
    with tempfile.NamedTemporaryFile(
        dir=dest.parent,
        prefix=f".{dest.name}.",
        suffix=suffix or dest.suffix,
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)
        tmp.close()

    try:
        yield tmp_path
        tmp_path.replace(dest)
    finally:
        tmp_path.unlink(missing_ok=True)


def prepare_destination(destination: str | Path) -> Path:
    """Ensure parent directory exists and return Path object."""
    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path
