from __future__ import annotations

import contextlib
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any, IO
from urllib.parse import urlparse


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


def is_remote_path(path: str | Path) -> bool:
    """Check if the path is a remote URI (e.g., s3://, gcs://)."""
    if isinstance(path, Path):
        return False
    parsed = urlparse(path)
    # Ignore single-letter schemes (Windows drives like C:/)
    return bool(parsed.scheme) and len(parsed.scheme) > 1 and parsed.scheme != "file"


def prepare_destination(destination: str | Path) -> Path | str:
    """Ensure parent directory exists for local paths. Returns input for remote URIs."""
    if is_remote_path(destination):
        return str(destination)

    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


@contextlib.contextmanager
def open_destination(
    destination: str | Path, mode: str = "w", **kwargs: Any
) -> Iterator[IO[Any]]:
    """
    Context manager that opens a destination for writing.
    Supports local paths and remote URIs via fsspec.
    """
    if is_remote_path(destination):
        try:
            import fsspec
        except ImportError:
            raise ImportError(
                f"fsspec is required for remote paths: {destination}. "
                "Install it with 'pip install fsspec' or pyreps[all]."
            ) from None

        with fsspec.open(destination, mode, **kwargs) as handle:
            yield handle  # type: ignore
    else:
        path = Path(destination)
        with path.open(mode, **kwargs) as handle:
            yield handle


def upload_to_remote(local_path: Path, remote_uri: str) -> None:
    """
    Upload a local file to a remote destination using fsspec's put().
    This allows native optimizations like parallel multipart uploads.
    """
    try:
        import fsspec
    except ImportError:
        raise ImportError(
            f"fsspec is required for uploading to remote paths: {remote_uri}. "
            "Install it with 'pip install fsspec' or pyreps[all]."
        ) from None

    fs, remote_path = fsspec.core.url_to_fs(remote_uri)
    fs.put(str(local_path), remote_path)


@contextlib.contextmanager
def local_render_path(
    destination: str | Path,
    suffix: str | None = None,
    progress_context: Any = None,
) -> Iterator[Path]:
    """
    Handle remote uploads for renderers that require a local file path.

    If destination is remote:
    1. Creates a temporary local file.
    2. Yields the local path.
    3. Uploads the local file to the remote destination on success.
    4. Automatically cleans up the temporary file in all cases.

    If destination is local:
    1. Ensures parent directory exists.
    2. Yields the Path object.
    """
    is_remote = is_remote_path(destination)

    if is_remote:
        # NamedTemporaryFile with delete=False so we can handle cleanup manually after upload
        tmp_handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        local_path = Path(tmp_handle.name)
        tmp_handle.close()
    else:
        local_path = Path(prepare_destination(destination))  # type: ignore

    try:
        yield local_path

        if is_remote:
            if progress_context and hasattr(progress_context, "set_stage"):
                progress_context.set_stage("uploading_to_cloud")
            upload_to_remote(local_path, str(destination))
    finally:
        if is_remote and local_path.exists():
            local_path.unlink()
