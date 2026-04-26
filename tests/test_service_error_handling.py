import pytest
from pyreps import generate_report, ReportSpec
from pyreps.contracts import ColumnSpec, InputAdapter
from pyreps.exceptions import InputAdapterError, MappingError


class BuggyAdapter(InputAdapter[list]):
    def __init__(self, fail_at: int):
        self.fail_at = fail_at

    def adapt(self, data: list):
        for i, item in enumerate(data):
            if i == self.fail_at:
                raise RuntimeError("Source connection dropped")
            yield item


def test_generate_report_adapter_streaming_failure(tmp_path):
    data = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    spec = ReportSpec(
        output_format="csv", columns=(ColumnSpec(label="name", source="name"),)
    )
    dest = tmp_path / "fail.csv"

    adapter = BuggyAdapter(fail_at=1)

    with pytest.raises(InputAdapterError) as excinfo:
        generate_report(
            data_source=data, spec=spec, destination=dest, input_adapter=adapter
        )

    assert excinfo.value.row_number == 1
    notes = getattr(excinfo.value, "__notes__", [])
    assert any("failure at row 1" in n for n in notes)
    assert not dest.exists()


def test_generate_report_mapping_failure(tmp_path):
    # Required field missing at row 2
    data = [{"name": "a"}, {"name": "b"}, {}]
    spec = ReportSpec(
        output_format="csv",
        columns=(ColumnSpec(label="Name", source="name", required=True),),
    )
    dest = tmp_path / "fail_map.csv"

    with pytest.raises(MappingError) as excinfo:
        generate_report(data_source=data, spec=spec, destination=dest)

    assert excinfo.value.row_number == 2
    notes = getattr(excinfo.value, "__notes__", [])
    assert any("failure at row 2" in n for n in notes)
    assert not dest.exists()


def test_generate_report_coercion_failure(tmp_path):
    data = [{"val": "1"}, {"val": "invalid"}, {"val": "3"}]
    spec = ReportSpec(
        output_format="csv",
        columns=(ColumnSpec(label="Value", source="val", type="int"),),
    )
    dest = tmp_path / "fail_coercion.csv"

    with pytest.raises(MappingError) as excinfo:  # CoercionError is a MappingError
        generate_report(data_source=data, spec=spec, destination=dest)

    assert excinfo.value.row_number == 1
    notes = getattr(excinfo.value, "__notes__", [])
    assert any("failure at row 1" in n for n in notes)
    assert not dest.exists()
