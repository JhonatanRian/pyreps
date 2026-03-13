from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .adapters import JsonAdapter, ListDictAdapter
from .contracts import InputAdapter, Renderer, ReportSpec
from .exceptions import InputAdapterError, ReportError
from .mapping import map_records
from .renderers import default_renderer_registry


def generate_report(
    *,
    data_source: Any,
    spec: ReportSpec,
    destination: str | Path,
    input_adapter: InputAdapter | None = None,
    renderer_registry: dict[str, Renderer] | None = None,
) -> Path:
    adapter = input_adapter or _resolve_adapter(data_source)
    records = list(adapter.adapt(data_source))
    mapped_rows = map_records(records, spec)

    registry = renderer_registry or default_renderer_registry()
    renderer = registry.get(spec.output_format)
    if renderer is None:
        raise ReportError(f"no renderer registered for format '{spec.output_format}'")

    return renderer.render(mapped_rows, spec, destination)


def _resolve_adapter(data_source: Any) -> InputAdapter:
    if isinstance(data_source, (str, bytes, bytearray)):
        return JsonAdapter()

    if isinstance(data_source, Mapping):
        return JsonAdapter()

    if isinstance(data_source, Iterable):
        return ListDictAdapter()

    raise InputAdapterError(
        "could not resolve input adapter automatically; pass input_adapter explicitly"
    )
