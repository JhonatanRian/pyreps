from __future__ import annotations

import logging
import time
from collections.abc import Generator, Iterable, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .adapters import JsonAdapter, ListDictAdapter
from .contracts import InputAdapter, Renderer, ReportSpec
from .exceptions import InputAdapterError, MappingError, ReportError
from .mapping import map_records
from .renderers import default_renderer_registry
from .utils.records import track_stream

logger = logging.getLogger("pyreps")


@contextmanager
def _report_transaction(
    destination: Path, output_format: str
) -> Generator[None, None, None]:
    """Encapsula telemetria e cleanup transacional para geração de relatórios."""
    start_time = time.perf_counter()
    try:
        yield
        elapsed = time.perf_counter() - start_time
        logger.info(
            "report generated: format=%s destination=%s time=%.3fs",
            output_format,
            destination,
            elapsed,
        )
    except Exception as exc:
        # Performance: unlink(missing_ok=True) é atômico e evita I/O redundante de .exists()
        destination.unlink(missing_ok=True)
        row_num = getattr(exc, "row_number", None)
        logger.error(
            "report generation failed: format=%s destination=%s row_number=%s error_type=%s",
            output_format,
            destination,
            row_num,
            type(exc).__name__,
        )
        raise


def generate_report[T](
    *,
    data_source: T,
    spec: ReportSpec,
    destination: str | Path,
    input_adapter: InputAdapter[T] | None = None,
    renderer_registry: dict[str, Renderer] | None = None,
) -> Path:
    adapter = input_adapter or _resolve_adapter(data_source)
    logger.debug("adapter resolved: %s", type(adapter).__name__)

    records = adapter.adapt(data_source)
    # Rastreia erros de streaming vindos do adaptador (ex: queda de conexão SQL)
    tracked_records = track_stream(records, "adapter", InputAdapterError)

    mapped_rows = map_records(tracked_records, spec)
    # Rastreia erros de mapeamento e coerção durante o streaming
    tracked_rows = track_stream(mapped_rows, "mapping", MappingError)

    registry = renderer_registry or default_renderer_registry()
    renderer = registry.get(spec.output_format)
    if renderer is None:
        raise ReportError(f"no renderer registered for format '{spec.output_format}'")

    output_path = Path(destination)
    with _report_transaction(output_path, spec.output_format):
        return renderer.render(tracked_rows, spec, output_path)


def _resolve_adapter(data_source: Any) -> InputAdapter[Any]:
    if isinstance(data_source, (str, bytes, bytearray)):
        return JsonAdapter()

    if isinstance(data_source, Mapping):
        return JsonAdapter()

    if isinstance(data_source, Iterable):
        return ListDictAdapter()

    raise InputAdapterError(
        "could not resolve input adapter automatically; pass input_adapter explicitly"
    )
