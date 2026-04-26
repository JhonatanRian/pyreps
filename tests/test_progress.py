import pytest
from pyreps import ColumnSpec, ReportSpec, generate_report
from pyreps.contracts import ProgressInfo


def test_progress_callback_csv(tmp_path):
    dest = tmp_path / "report.csv"
    data = [{"name": f"user_{i}", "age": i} for i in range(2500)]
    spec = ReportSpec(
        columns=(
            ColumnSpec(label="Name", source="name"),
            ColumnSpec(label="Age", source="age"),
        ),
        output_format="csv",
    )

    captured_progress = []

    def progress_callback(info: ProgressInfo):
        captured_progress.append(info)

    generate_report(
        data_source=data,
        spec=spec,
        destination=dest,
        progress_callback=progress_callback,
        total_rows=2500,
    )

    # Stages expected in order (approximate as set_stage fires callback)
    # initializing (default) -> resolving_adapter -> adapting_data -> mapping_records ->
    # writing_rows -> 1000 rows -> 2000 rows -> 2500 rows -> finalizing -> finish
    
    stages = [p.current_stage for p in captured_progress]
    assert "resolving_adapter" in stages
    assert "writing_rows" in stages
    assert "finalizing" in stages

    # Check row counts
    processed_counts = [p.total_rows_processed for p in captured_progress]
    assert 1000 in processed_counts
    assert 2000 in processed_counts
    assert 2500 in processed_counts

    # Check estimated completion
    final_info = captured_progress[-1]
    assert final_info.total_rows_processed == 2500
    assert final_info.estimated_completion is not None
    assert final_info.estimated_completion >= final_info.elapsed_seconds


def test_progress_callback_xlsx(tmp_path):
    dest = tmp_path / "report.xlsx"
    data = [{"name": f"user_{i}", "age": i} for i in range(1500)]
    spec = ReportSpec(
        columns=(
            ColumnSpec(label="Name", source="name"),
            ColumnSpec(label="Age", source="age"),
        ),
        output_format="xlsx",
    )

    captured_progress = []

    def progress_callback(info: ProgressInfo):
        captured_progress.append(info)

    generate_report(
        data_source=data,
        spec=spec,
        destination=dest,
        progress_callback=progress_callback,
    )

    stages = [p.current_stage for p in captured_progress]
    assert "writing_xlsx_rows" in stages
    assert "finalizing_xlsx" in stages
    
    processed_counts = [p.total_rows_processed for p in captured_progress]
    assert 1000 in processed_counts
    assert 1500 in processed_counts


def test_progress_callback_pdf(tmp_path):
    dest = tmp_path / "report.pdf"
    data = [{"name": f"user_{i}", "age": i} for i in range(500)]
    spec = ReportSpec(
        columns=(
            ColumnSpec(label="Name", source="name"),
            ColumnSpec(label="Age", source="age"),
        ),
        output_format="pdf",
    )

    captured_progress = []

    def progress_callback(info: ProgressInfo):
        captured_progress.append(info)

    generate_report(
        data_source=data,
        spec=spec,
        destination=dest,
        progress_callback=progress_callback,
    )

    stages = [p.current_stage for p in captured_progress]
    assert "preparing_pdf_document" in stages
    assert "writing_pdf_rows" in stages
    assert "finalizing_pdf" in stages
    
    assert captured_progress[-1].total_rows_processed == 500
