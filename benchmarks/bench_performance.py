"""Performance and memory benchmarks for pyreps.

Measures wall-clock time and peak Python-level memory (tracemalloc)
for each output format across different dataset sizes.
"""

from __future__ import annotations

import gc
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

from py_reports import ColumnSpec, ReportSpec, generate_report


# ── Dataset generator (never materializes full list) ─────────────────

def _generate_records(n: int):
    """Yield n records lazily — zero upfront memory."""
    for i in range(n):
        yield {
            "id": i,
            "name": f"Customer {i}",
            "email": f"customer{i}@example.com",
            "amount": round(i * 1.37, 2),
            "status": "active" if i % 3 else "inactive",
            "region": ["north", "south", "east", "west"][i % 4],
        }


COLUMNS = [
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


def _run_benchmark(fmt: str, spec: ReportSpec, n: int, tmpdir: Path) -> dict:
    gc.collect()
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    t0 = time.perf_counter()

    dest = tmpdir / f"bench_{fmt}_{n}.{fmt}"
    result_path = generate_report(
        data_source=_generate_records(n),
        spec=spec,
        destination=str(dest),
    )

    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    file_size = result_path.stat().st_size

    return {
        "format": fmt,
        "records": n,
        "time_s": round(elapsed, 3),
        "peak_mem_mb": round(peak / (1024 * 1024), 2),
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "rows_per_sec": int(n / elapsed) if elapsed > 0 else 0,
    }


def main():
    sizes = [1_000, 10_000, 100_000, 500_000]
    formats = [
        ("csv", SPEC_CSV),
        ("xlsx", SPEC_XLSX),
    ]
    pdf_sizes = [1_000, 10_000]

    header = f"{'Format':<8} {'Records':>10} {'Time (s)':>10} {'Peak RAM (MB)':>14} {'File (MB)':>10} {'rows/s':>10}"
    sep = "=" * len(header)

    print(sep)
    print(header)
    print(sep)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        for fmt, spec in formats:
            for n in sizes:
                r = _run_benchmark(fmt, spec, n, tmp)
                print(
                    f"{r['format']:<8} {r['records']:>10,} {r['time_s']:>10.3f} "
                    f"{r['peak_mem_mb']:>14.2f} {r['file_size_mb']:>10.2f} {r['rows_per_sec']:>10,}"
                )
            print("-" * len(header))

        for n in pdf_sizes:
            r = _run_benchmark("pdf", SPEC_PDF, n, tmp)
            print(
                f"{r['format']:<8} {r['records']:>10,} {r['time_s']:>10.3f} "
                f"{r['peak_mem_mb']:>14.2f} {r['file_size_mb']:>10.2f} {r['rows_per_sec']:>10,}"
            )

    print(sep)


if __name__ == "__main__":
    main()
