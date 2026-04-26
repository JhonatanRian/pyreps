import gc
import pytest
import tempfile
from pathlib import Path
from typing import Any, Generator

from pyreps import ColumnSpec, ReportSpec, generate_report
from tests.utils_memory import MemoryTracker


def _generate_data(n: int) -> Generator[dict[str, Any], None, None]:
    """Lazy generator to ensure O(1) input memory."""
    for i in range(n):
        yield {
            "id": i,
            "name": f"User {i}",
            "value": i * 1.5,
            "status": "active" if i % 2 == 0 else "inactive"
        }


COLUMNS: list[ColumnSpec] = [
    ColumnSpec(label="ID", source="id", type="int"),
    ColumnSpec(label="Name", source="name", type="str"),
    ColumnSpec(label="Value", source="value", type="float"),
    ColumnSpec(label="Status", source="status", type="str"),
]


@pytest.mark.memory
@pytest.mark.parametrize("fmt", ["csv", "xlsx"])
def test_memory_threshold_1m_rows(fmt: str) -> None:
    """
    Threshold Test: 1M rows should stay under 100MB of peak RSS.
    This ensures that even with a large dataset, memory usage is controlled.
    """
    spec = ReportSpec(columns=COLUMNS, output_format=fmt)
    
    gc.collect()
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir) / f"test_threshold.{fmt}"
        
        with MemoryTracker() as tracker:
            generate_report(
                data_source=_generate_data(1_000_000),
                spec=spec,
                destination=str(dest)
            )
        
        result = tracker.result
            
    # Threshold: 100MB
    assert result.peak_rss_mb < 100, f"Peak memory for {fmt} was {result.peak_rss_mb:.2f}MB, exceeding 100MB"


@pytest.mark.memory
@pytest.mark.parametrize("fmt", ["csv", "xlsx"])
def test_memory_linearity_o1(fmt: str) -> None:
    """
    Linearity (O(1)) Test: Memory usage should NOT grow linearly with row count.
    We compare peak RSS at 10k rows vs 100k rows.
    """
    spec = ReportSpec(columns=COLUMNS, output_format=fmt)
    
    # Measure 10k rows
    gc.collect()
    with tempfile.TemporaryDirectory() as tmpdir:
        dest_10k = Path(tmpdir) / f"test_10k.{fmt}"
        with MemoryTracker() as tracker:
            generate_report(data_source=_generate_data(10_000), spec=spec, destination=str(dest_10k))
        res_10k = tracker.result
            
    # Measure 100k rows
    gc.collect()
    with tempfile.TemporaryDirectory() as tmpdir:
        dest_100k = Path(tmpdir) / f"test_100k.{fmt}"
        with MemoryTracker() as tracker:
            generate_report(data_source=_generate_data(100_000), spec=spec, destination=str(dest_100k))
        res_100k = tracker.result
            
    # O(1) validation: Memory at 100k should be very close to 10k.
    # We allow a small tolerance (e.g., 10MB) for process overhead and fragmentation.
    tolerance = 10.0
    diff = res_100k.peak_rss_mb - res_10k.peak_rss_mb
    
    assert diff < tolerance, (
        f"Memory grew by {diff:.2f}MB between 10k and 100k rows for {fmt}. "
        f"10k: {res_10k.peak_rss_mb:.2f}MB, 100k: {res_100k.peak_rss_mb:.2f}MB"
    )


@pytest.mark.memory
def test_memory_pdf_threshold_10k_rows() -> None:
    """
    PDF Threshold: PDF is NOT a streaming format in pyreps (it materializes layout).
    We still want to monitor it for regressions, but with a smaller dataset and higher threshold.
    """
    spec = ReportSpec(columns=COLUMNS, output_format="pdf")
    
    gc.collect()
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir) / "test_pdf.pdf"
        
        with MemoryTracker() as tracker:
            generate_report(
                data_source=_generate_data(10_000),
                spec=spec,
                destination=str(dest)
            )
        result = tracker.result
            
    # PDF is more memory-intensive
    assert result.peak_rss_mb < 200, f"Peak memory for PDF was {result.peak_rss_mb:.2f}MB"
