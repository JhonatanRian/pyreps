from __future__ import annotations

import itertools
import logging
import time
from collections.abc import Generator, Iterable, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .adapters import JsonAdapter, ListDictAdapter
from .contracts import (
    InputAdapter,
    NullProgressContext,
    ProgressCallback,
    ProgressContext,
    ProgressInfo,
    Record,
    Renderer,
    ReportSpec,
)
from .exceptions import InputAdapterError, MappingError, ReportError
from .mapping import map_records
from .renderers import default_renderer_registry
from .utils.files import prepare_destination
from .utils.records import track_stream

from dataclasses import dataclass, field

logger = logging.getLogger("pyreps")


@contextmanager
def _report_transaction(
    destination: Path | str, output_format: str
) -> Generator[None, None, None]:
    """Encapsulates telemetry and transactional cleanup for report generation."""
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
        if isinstance(destination, Path):
            destination.unlink(missing_ok=True)
        # Remote cleanup is handled by renderers' finally block or fsspec transactional open
        row_num = getattr(exc, "row_number", None)
        logger.error(
            "report generation failed: format=%s destination=%s row_number=%s error_type=%s",
            output_format,
            destination,
            row_num,
            type(exc).__name__,
        )
        raise



@dataclass(slots=True)
class ReportProgressContext(ProgressContext):
    """Default implementation for progress tracking in report generation."""

    callback: ProgressCallback
    total_rows: int | None = None
    current_stage: str = "initializing"
    start_time: float = field(default_factory=time.perf_counter)
    total_processed: int = 0

    def set_stage(self, stage_name: str) -> None:
        self.current_stage = stage_name
        self._fire_callback(self.total_processed)

    def track_rows(
        self, rows: Iterable[Record], chunk_size: int = 1000
    ) -> Generator[Record, None, None]:
        # Performance: itertools.batched (C implementation) is ~2x faster than
        # manual countdown for grouping rows in Python 3.12+.
        processed = self.total_processed
        fire = self._fire_callback

        for chunk in itertools.batched(rows, chunk_size):
            for row in chunk:
                yield row
            processed += len(chunk)
            self.total_processed = processed
            fire(processed)

    def finish(self) -> None:
        self._fire_callback(self.total_processed)

    def _fire_callback(self, rows_processed: int) -> None:
        elapsed = time.perf_counter() - self.start_time
        estimated_completion = None

        if self.total_rows and rows_processed > 0:
            # Simple linear estimation
            estimated_completion = (elapsed / rows_processed) * self.total_rows

        self.callback(
            ProgressInfo(
                total_rows_processed=rows_processed,
                current_stage=self.current_stage,
                elapsed_seconds=elapsed,
                estimated_completion=estimated_completion,
            )
        )


def generate_report[T](
    *,
    data_source: T,
    spec: ReportSpec,
    destination: str | Path,
    input_adapter: InputAdapter[T] | None = None,
    renderer_registry: dict[str, Renderer] | None = None,
    progress_callback: ProgressCallback | None = None,
    total_rows: int | None = None,
) -> Path | str:
    progress_ctx: ProgressContext = (
        ReportProgressContext(progress_callback, total_rows)
        if progress_callback
        else NullProgressContext()
    )

    progress_ctx.set_stage("resolving_adapter")

    adapter = input_adapter or _resolve_adapter(data_source)
    logger.debug("adapter resolved: %s", type(adapter).__name__)

    progress_ctx.set_stage("adapting_data")

    records = adapter.adapt(data_source)
    # Tracks streaming errors from the adapter (e.g. SQL connection drop)
    tracked_records = track_stream(records, "adapter", InputAdapterError)

    progress_ctx.set_stage("mapping_records")

    mapped_rows = map_records(tracked_records, spec)
    # Tracks mapping and coercion errors during streaming
    tracked_rows = track_stream(mapped_rows, "mapping", MappingError)

    registry = renderer_registry or default_renderer_registry()
    renderer = registry.get(spec.output_format)
    if renderer is None:
        raise ReportError(f"no renderer registered for format '{spec.output_format}'")

    output_path = prepare_destination(destination)
    with _report_transaction(output_path, spec.output_format):
        result = renderer.render(
            tracked_rows, spec, output_path, progress_context=progress_ctx
        )

    progress_ctx.finish()

    return result


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
