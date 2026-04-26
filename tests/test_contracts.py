import pytest
from pyreps.contracts import ColumnSpec, ReportSpec
from pyreps.exceptions import InvalidSpecError


def test_column_spec_valid_init():
    """Verify valid ColumnSpec initialization."""
    col = ColumnSpec(label="Name", source="name", type="str")
    assert col.label == "Name"
    assert col.source == "name"
    assert col._source_parts == ("name",)


@pytest.mark.parametrize(
    "label, source",
    [
        ("", "name"),
        (None, "name"),
        ("Name", ""),
        ("Name", None),
    ],
)
def test_column_spec_invalid_label_or_source(label, source):
    """Verify ColumnSpec raises InvalidSpecError for invalid label or source."""
    with pytest.raises(InvalidSpecError, match="must be a non-empty string"):
        ColumnSpec(label=label, source=source)


def test_column_spec_invalid_type():
    """Verify ColumnSpec raises InvalidSpecError for invalid type."""
    with pytest.raises(InvalidSpecError, match="Invalid column type 'invalid'"):
        ColumnSpec(label="Name", source="name", type="invalid")


def test_column_spec_invalid_formatter():
    """Verify ColumnSpec raises InvalidSpecError for non-callable formatter."""
    with pytest.raises(InvalidSpecError, match="formatter must be callable"):
        ColumnSpec(label="Name", source="name", formatter="not a function")


def test_report_spec_valid_init():
    """Verify valid ReportSpec initialization."""
    cols = (ColumnSpec(label="Name", source="name"),)
    spec = ReportSpec(columns=cols, output_format="csv")
    assert spec.columns == cols
    assert spec.labels == ("Name",)


def test_report_spec_empty_columns():
    """Verify ReportSpec raises InvalidSpecError if no columns are provided."""
    with pytest.raises(InvalidSpecError, match="at least one column"):
        ReportSpec(columns=())


def test_report_spec_invalid_format():
    """Verify ReportSpec raises InvalidSpecError for invalid output_format."""
    cols = (ColumnSpec(label="Name", source="name"),)
    with pytest.raises(InvalidSpecError, match="Invalid output format 'json'"):
        ReportSpec(columns=cols, output_format="json")


def test_report_spec_duplicate_labels():
    """Verify ReportSpec raises InvalidSpecError for duplicate column labels."""
    cols = (
        ColumnSpec(label="Name", source="first_name"),
        ColumnSpec(label="Name", source="last_name"),
    )
    with pytest.raises(InvalidSpecError, match="Duplicate column labels detected"):
        ReportSpec(columns=cols)


def test_report_spec_metadata_immutability():
    """Verify metadata is converted to an immutable MappingProxyType."""
    cols = (ColumnSpec(label="Name", source="name"),)
    spec = ReportSpec(columns=cols, metadata={"csv": {"delimiter": ";"}})
    with pytest.raises(TypeError):
        spec.metadata["csv"] = {}  # type: ignore
