"""Performance and memory benchmarks for pyreps.
Outputs results to terminal and memory_report.md.
"""

from __future__ import annotations

import gc
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

from pyreps import ColumnSpec, ReportSpec, generate_report
from tests.utils_memory import MemoryTracker


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Stores benchmark metrics for a single run."""
    format: str
    records: int
    time_s: float
    peak_mem_mb: float
    file_size_mb: float
    rows_per_sec: int


def _generate_records(n: int) -> Generator[dict[str, Any], None, None]:
    """Yield n records lazily."""
    for i in range(n):
        yield {
            "id": i,
            "name": f"Customer {i}",
            "email": f"customer{i}@example.com",
            "amount": round(i * 1.37, 2),
            "status": "active" if i % 3 else "inactive",
            "region": ["north", "south", "east", "west"][i % 4],
        }


COLUMNS: list[ColumnSpec] = [
    ColumnSpec(label="ID", source="id", type="int"),
    ColumnSpec(label="Name", source="name", type="str"),
    ColumnSpec(label="Email", source="email", type="str"),
    ColumnSpec(label="Amount", source="amount", type="float"),
    ColumnSpec(label="Status", source="status", type="str"),
    ColumnSpec(label="Region", source="region", type="str"),
]

SPEC_CSV = ReportSpec(columns=COLUMNS, output_format="csv")
SPEC_XLSX = ReportSpec(columns=COLUMNS, output_format="xlsx")
SPEC_PDF = ReportSpec(columns=COLUMNS, output_format="pdf")


def _run_benchmark(fmt: str, spec: ReportSpec, n: int, tmpdir: Path) -> BenchmarkResult:
    """Executes a single benchmark run and captures performance data."""
    gc.collect()
    
    t0 = time.perf_counter()
    dest = tmpdir / f"bench_{fmt}_{n}.{fmt}"
    
    with MemoryTracker() as tracker:
        result_path = generate_report(
            data_source=_generate_records(n),
            spec=spec,
            destination=str(dest),
        )
    
    elapsed = time.perf_counter() - t0
    peak_mb = tracker.result.peak_rss_mb
    file_size = result_path.stat().st_size

    return BenchmarkResult(
        format=fmt,
        records=n,
        time_s=round(elapsed, 3),
        peak_mem_mb=round(peak_mb, 2),
        file_size_mb=round(file_size / (1024 * 1024), 2),
        rows_per_sec=int(n / elapsed) if elapsed > 0 else 0,
    )


def save_markdown_report(results: list[BenchmarkResult], output_path: str = "memory_report.md") -> None:
    """Generates a Markdown report from benchmark results."""
    md_lines = [
        "# Memory & Performance Report",
        "",
        "| Format | Records | Time (s) | Peak RAM (MB) | File (MB) | Rows/s |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |"
    ]
    
    for r in results:
        line = f"| {r.format} | {r.records:,} | {r.time_s:.3f} | {r.peak_mem_mb:.2f} | {r.file_size_mb:.2f} | {r.rows_per_sec:,} |"
        md_lines.append(line)

    Path(output_path).write_text("\n".join(md_lines))
    print(f"\nReport generated: {output_path}")


def print_console_table(results: list[BenchmarkResult]) -> None:
    """Prints a formatted table of results to the console."""
    header = f"{'Format':<8} {'Records':>10} {'Time (s)':>10} {'Peak RAM (MB)':>14} {'File (MB)':>10} {'rows/s':>10}"
    print("\n" + "=" * len(header))
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r.format:<8} {r.records:>10,} {r.time_s:>10.3f} "
            f"{r.peak_mem_mb:>14.2f} {r.file_size_mb:>10.2f} {r.rows_per_sec:>10,}"
        )
    print("=" * len(header))


def main() -> None:
    sizes = [10_000, 100_000, 500_000]
    formats = [
        ("csv", SPEC_CSV),
        ("xlsx", SPEC_XLSX),
    ]
    pdf_sizes = [10_000]

    results: list[BenchmarkResult] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        for fmt, spec in formats:
            for n in sizes:
                r = _run_benchmark(fmt, spec, n, tmp)
                results.append(r)
                print(f"Benchmarked {fmt} {n:,} rows...")

        for n in pdf_sizes:
            r = _run_benchmark("pdf", SPEC_PDF, n, tmp)
            results.append(r)
            print(f"Benchmarked pdf {n:,} rows...")

    save_markdown_report(results)
    print_console_table(results)


if __name__ == "__main__":
    main()
