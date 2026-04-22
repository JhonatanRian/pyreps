from __future__ import annotations

import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal, Mapping

from .exceptions import ReportError
from .utils.options import coerce_number, coerce_optional_number

WidthMode = Literal["manual", "auto", "mixed"]
_VALID_MODES = {"manual", "auto", "mixed"}
_INVALID_SHEET_CHARS = re.compile(r"[\\/*?\[\]:]")
_MAX_SHEET_NAME_LEN = 31


@dataclass(slots=True, frozen=True)
class XlsxColumnOptions:
    width: float | None = None
    min_width: float | None = None
    max_width: float | None = None

    def __post_init__(self) -> None:
        if self.width is not None and self.width < 0.1:
            raise ReportError("xlsx column width must be >= 0.1")
        if self.min_width is not None and self.min_width < 0.1:
            raise ReportError("xlsx column min_width must be >= 0.1")
        if self.max_width is not None and self.max_width < 0.1:
            raise ReportError("xlsx column max_width must be >= 0.1")
        if (
            self.min_width is not None
            and self.max_width is not None
            and self.min_width > self.max_width
        ):
            raise ReportError("xlsx column min_width cannot be greater than max_width")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], label: str = "label") -> XlsxColumnOptions:
        return cls(
            width=coerce_optional_number(
                value.get("width"),
                field_name=f"metadata['xlsx']['columns']['{label}']['width']",
                min_value=0.1,
            ),
            min_width=coerce_optional_number(
                value.get("min_width"),
                field_name=f"metadata['xlsx']['columns']['{label}']['min_width']",
                min_value=0.1,
            ),
            max_width=coerce_optional_number(
                value.get("max_width"),
                field_name=f"metadata['xlsx']['columns']['{label}']['max_width']",
                min_value=0.1,
            ),
        )


@dataclass(slots=True, frozen=True)
class XlsxRenderOptions:
    width_mode: WidthMode = "mixed"
    default_width: float = 12.0
    auto_padding: float = 1.5
    sheet_name: str = "Report"
    columns: Mapping[str, XlsxColumnOptions] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.width_mode not in _VALID_MODES:
            raise ReportError("metadata['xlsx']['width_mode'] must be manual, auto or mixed")
        if self.default_width < 0.1:
            raise ReportError("metadata['xlsx']['default_width'] must be >= 0.1")
        if self.auto_padding < 0.0:
            raise ReportError("metadata['xlsx']['auto_padding'] must be >= 0")

        # Normalize and validate sheet_name
        name = _coerce_sheet_name(self.sheet_name)
        object.__setattr__(self, "sheet_name", name)

        # Freeze the columns dict to prevent mutation in a frozen dataclass
        if not isinstance(self.columns, MappingProxyType):
            object.__setattr__(self, "columns", MappingProxyType(dict(self.columns)))

    @classmethod
    def from_metadata(cls, metadata: Mapping[str, Any]) -> XlsxRenderOptions:
        raw_xlsx = metadata.get("xlsx", {})
        if not isinstance(raw_xlsx, Mapping):
            raise ReportError("metadata['xlsx'] must be a mapping")

        columns_raw = raw_xlsx.get("columns", {})
        if not isinstance(columns_raw, Mapping):
            raise ReportError("metadata['xlsx']['columns'] must be a mapping")

        parsed_columns: dict[str, XlsxColumnOptions] = {}
        for label, options in columns_raw.items():
            if not isinstance(label, str):
                raise ReportError("metadata['xlsx']['columns'] keys must be strings")
            if not isinstance(options, Mapping):
                raise ReportError(f"metadata['xlsx']['columns']['{label}'] must be a mapping")
            parsed_columns[label] = XlsxColumnOptions.from_mapping(options, label=label)

        return cls(
            width_mode=raw_xlsx.get("width_mode", "mixed"),
            default_width=coerce_number(
                raw_xlsx.get("default_width", 12.0),
                field_name="metadata['xlsx']['default_width']",
                min_value=0.1,
            ),
            auto_padding=coerce_number(
                raw_xlsx.get("auto_padding", 1.5),
                field_name="metadata['xlsx']['auto_padding']",
                min_value=0.0,
            ),
            sheet_name=raw_xlsx.get("sheet_name", "Report"),
            columns=parsed_columns,
        )


def _coerce_sheet_name(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReportError("metadata['xlsx']['sheet_name'] must be a non-empty string")

    name = value.strip()
    if len(name) > _MAX_SHEET_NAME_LEN:
        raise ReportError(
            f"metadata['xlsx']['sheet_name'] exceeds Excel limit of {_MAX_SHEET_NAME_LEN} characters"
        )
    if _INVALID_SHEET_CHARS.search(name):
        raise ReportError(
            "metadata['xlsx']['sheet_name'] contains invalid Excel characters: \\ / * ? : [ ]"
        )
    if name.startswith("'") or name.endswith("'"):
        raise ReportError("metadata['xlsx']['sheet_name'] cannot start or end with apostrophe")

    return name
