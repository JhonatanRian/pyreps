from __future__ import annotations

import pytest
from types import MappingProxyType

from py_reports.exceptions import ReportError
from py_reports.xlsx_options import XlsxColumnOptions, XlsxRenderOptions


def test_xlsx_options_sheet_name_validations() -> None:
    # Test valid sheet name
    opts = XlsxRenderOptions.from_metadata({"xlsx": {"sheet_name": "Valid Name"}})
    assert opts.sheet_name == "Valid Name"

    # Test normalization (strip) even in manual instantiation
    opts = XlsxRenderOptions(sheet_name="  Spaces  ")
    assert opts.sheet_name == "Spaces"

    # Test max length (31 chars)
    with pytest.raises(ReportError, match="exceeds Excel limit of 31 characters"):
        XlsxRenderOptions(sheet_name="A" * 32)

    # Test invalid characters
    for char in r"\/*?[]:":
        with pytest.raises(ReportError, match="contains invalid Excel characters"):
            XlsxRenderOptions(sheet_name=f"Invalid{char}Name")

    # Test starts/ends with apostrophe
    with pytest.raises(ReportError, match="cannot start or end with apostrophe"):
        XlsxRenderOptions(sheet_name="'InvalidName")

    with pytest.raises(ReportError, match="cannot start or end with apostrophe"):
        XlsxRenderOptions(sheet_name="InvalidName'")


def test_xlsx_options_columns_immutability() -> None:
    opts = XlsxRenderOptions(columns={"ID": XlsxColumnOptions(width=10)})

    # Attempting to mutate the columns dict should raise TypeError (MappingProxyType is read-only)
    with pytest.raises(TypeError, match="does not support item assignment"):
        opts.columns["ID"] = XlsxColumnOptions(width=20)  # type: ignore

    # MappingProxyType doesn't even have mutation methods
    with pytest.raises(AttributeError):
        opts.columns.clear()  # type: ignore


def test_xlsx_options_post_init_preserves_mapping_proxy() -> None:
    # Ensure __post_init__ doesn't wrap it twice if it's already a MappingProxyType
    proxy = MappingProxyType({"ID": XlsxColumnOptions(width=10)})
    opts = XlsxRenderOptions(columns=proxy)
    assert opts.columns is proxy


def test_xlsx_column_options_error_messages() -> None:
    # Check if error message contains the specific column label
    with pytest.raises(ReportError, match=r"metadata\['xlsx'\]\['columns'\]\['PRICE'\]\['width'\]"):
        XlsxColumnOptions.from_mapping({"width": -1}, label="PRICE")
