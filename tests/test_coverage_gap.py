
import pytest
import re
from pyreps import __version__
from pyreps.xlsx_options import XlsxRenderOptions, XlsxColumnOptions
from pyreps.exceptions import ReportError

def test_version_access() -> None:
    assert isinstance(__version__, str)
    assert __version__ != "0.0.0-dev"

def test_xlsx_options_validation_gaps() -> None:
    # metadata['xlsx'] not a mapping
    with pytest.raises(ReportError, match=re.escape("metadata['xlsx'] must be a mapping")):
        XlsxRenderOptions.from_metadata({"xlsx": "invalid"})
    
    # metadata['xlsx']['columns'] not a mapping
    with pytest.raises(ReportError, match=re.escape("metadata['xlsx']['columns'] must be a mapping")):
        XlsxRenderOptions.from_metadata({"xlsx": {"columns": []}})
        
    # column label not a string
    with pytest.raises(ReportError, match=re.escape("metadata['xlsx']['columns'] keys must be strings")):
        XlsxRenderOptions.from_metadata({"xlsx": {"columns": {1: {}}}})
        
    # column options not a mapping
    with pytest.raises(ReportError, match=re.escape("metadata['xlsx']['columns']['A'] must be a mapping")):
        XlsxRenderOptions.from_metadata({"xlsx": {"columns": {"A": "invalid"}}})

def test_sheet_name_validation_gaps() -> None:
    # Empty sheet name
    with pytest.raises(ReportError, match=re.escape("sheet_name'] must be a non-empty string")):
        XlsxRenderOptions(sheet_name="  ")
        
    # Too long
    with pytest.raises(ReportError, match=re.escape("exceeds Excel limit of 31 characters")):
        XlsxRenderOptions(sheet_name="A" * 32)
        
    # Invalid characters
    for char in "\\/*?[]:":
        with pytest.raises(ReportError, match=re.escape("contains invalid Excel characters")):
            XlsxRenderOptions(sheet_name=f"Sheet{char}")
            
    # Apostrophe
    with pytest.raises(ReportError, match=re.escape("cannot start or end with apostrophe")):
        XlsxRenderOptions(sheet_name="'Sheet'")

def test_xlsx_column_options_validation_gaps() -> None:
    # Negative width
    with pytest.raises(ReportError, match=re.escape("width must be >= 0.1")):
        XlsxColumnOptions(width=0.05)
    with pytest.raises(ReportError, match=re.escape("min_width must be >= 0.1")):
        XlsxColumnOptions(min_width=0.05)
    with pytest.raises(ReportError, match=re.escape("max_width must be >= 0.1")):
        XlsxColumnOptions(max_width=0.05)
    with pytest.raises(ReportError, match=re.escape("min_width cannot be greater than max_width")):
        XlsxColumnOptions(min_width=20, max_width=10)
