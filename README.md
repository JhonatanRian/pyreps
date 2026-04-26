<div align="center">

# pyreps

**Python report generation — CSV, XLSX, and PDF with Rust performance.** ⚡

[![CI](https://github.com/JhonatanRian/pyreps/actions/workflows/ci.yml/badge.svg)](https://github.com/JhonatanRian/pyreps/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/JhonatanRian/pyreps/graph/badge.svg?token=)](https://codecov.io/gh/JhonatanRian/pyreps)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[Documentation](https://JhonatanRian.github.io/pyreps/) · [PyPI](https://pypi.org/project/pyreps/) · [Issues](https://github.com/JhonatanRian/pyreps/issues)

</div>

---

## ✨ Highlights

- **🚀 High Performance** — 100% streaming pipeline. CSV and XLSX use < 1 MB of RAM with 500K+ rows.
- **🦀 Powered by Rust** — XLSX via `rustpy-xlsxwriter`, JSON via `orjson`.
- **📄 3 Formats** — CSV, XLSX, and PDF with a single API.
- **🔌 Pluggable** — Supports `list[dict]`, JSON, SQL, or any custom source.
- **🎯 Declarative Types** — Automatic coercion for `int`, `float`, `bool`, `date`, `datetime`.
- **🪶 Lightweight** — 3 runtime dependencies. No pandas, no numpy.

## Installation

```bash
pip install pyreps
```

## Quickstart

```python
from pyreps import ColumnSpec, ReportSpec, generate_report

# data sample
data = [
    {"id": 1, "customer": {"name": "Ana"}, "total": 100.50},
    {"id": 2, "customer": {"name": "Bruno"}, "total": 250.00},
]

spec = ReportSpec(
    output_format="csv",  # or "xlsx" or "pdf"
    columns=[
        ColumnSpec(label="ID", source="id", type="int", required=True),
        ColumnSpec(label="Customer", source="customer.name"),
        ColumnSpec(label="Total", source="total", type="float",
                   formatter=lambda v: f"$ {v:.2f}"),
    ],
)

path = generate_report(data_source=data, spec=spec, destination="sales.csv")
```

## Supported Formats

| Format | Renderer | Engine | Streaming |
|---------|----------|-------|-----------|
| CSV | `CsvRenderer` | `csv` stdlib (C) | ✅ Constant memory |
| XLSX | `XlsxRenderer` | `rustpy-xlsxwriter` (Rust) | ✅ Constant memory |
| PDF | `PdfRenderer` | `reportlab` (C) | ⚠️ Materializes (layout) |

## Data Sources

| Source | Adapter | Detection |
|-------|---------|----------|
| `list[dict]` / generator | `ListDictAdapter` | Automatic |
| JSON string / bytes | `JsonAdapter` | Automatic |
| `dict` / `Mapping` | `JsonAdapter` | Automatic |
| SQL query | `SqlAdapter` | Explicit |
| Custom | Implement `InputAdapter` | Explicit |

## Declarative Types

```python
ColumnSpec(label="Created", source="created_at", type="date")
ColumnSpec(label="Active", source="active", type="bool")    # "yes" → True
ColumnSpec(label="Total", source="total", type="float")     # "3.14" → 3.14
```

Types: `str`, `int`, `float`, `bool`, `date`, `datetime`. Optional — `type=None` maintains pass-through.

## XLSX — Column Widths

```python
spec = ReportSpec(
    output_format="xlsx",
    columns=[...],
    metadata={
        "xlsx": {
            "width_mode": "auto",     # "manual" | "auto" | "mixed"
            "sheet_name": "Sales",
            "columns": {
                "ID": {"width": 8.0},
                "Description": {"min_width": 20.0, "max_width": 50.0},
            },
        }
    },
)
```

## SQL

```python
from pyreps import SqlAdapter

generate_report(
    data_source=None,
    spec=spec,
    destination="sales.csv",
    input_adapter=SqlAdapter(
        query="SELECT id, name, total FROM sales",
        connection=connection,
    ),
)
```

## Performance

Benchmark with 6 columns and declarative types:

| Format | 500K rows | Peak RAM | rows/s |
|---------|------------|----------|--------|
| CSV | 15s | **0.16 MB** | ~33K |
| XLSX | 24s | **0.62 MB** | ~21K |

> CSV and XLSX maintain constant memory regardless of volume.

## Documentation

📖 Complete documentation at [JhonatanRian.github.io/pyreps](https://JhonatanRian.github.io/pyreps/)

## License

MIT
