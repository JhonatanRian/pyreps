# Output Formats

**{{ project_name }}** supports three output formats, all configurable via `ReportSpec.metadata`.

## CSV

The simplest and most performant format. Pure streaming — constant memory.

```python
spec = ReportSpec(
    output_format="csv",
    columns=[...],
    metadata={
        "csv": {
            "delimiter": ";",  # default: ","
        }
    },
)
```

| Option | Type | Default | Description |
|-------|------|--------|-----------|
| `delimiter` | `str` | `","` | Field separator |

---

## XLSX

Generated via **Rust** (`{{ rust_lib }}`) with automatic column width support.

### Full Example

```python
spec = ReportSpec(
    output_format="xlsx",
    columns=[...],
    metadata={
        "xlsx": {
            "width_mode": "mixed",
            "default_width": 14.0,
            "auto_padding": 2.0,
            "sheet_name": "Report",
            "columns": {
                "Description": {"min_width": 20.0, "max_width": 50.0},
                "ID": {"width": 8.0},
            },
        }
    },
)
```

### Global Options

| Option | Type | Default | Description |
|-------|------|--------|-----------|
| `width_mode` | `str` | `"mixed"` | Width calculation mode |
| `default_width` | `float` | `12.0` | Default width (manual mode) |
| `auto_padding` | `float` | `1.5` | Extra padding (auto mode) |
| `sheet_name` | `str` | `"Report"` | Sheet name |
| `columns` | `dict` | `{}` | Per-column configuration |

### Width Modes

=== "manual"

    All columns use `default_width`, except those with an explicit `width`.

    ```python
    {"width_mode": "manual", "default_width": 15.0}
    ```

=== "auto"

    Calculates width based on the largest content in each column.

    ```python
    {"width_mode": "auto", "auto_padding": 2.0}
    ```

=== "mixed (recommended)"

    Uses explicit `width` when defined; otherwise, calculates it automatically.

    ```python
    {
        "width_mode": "mixed",
        "columns": {"ID": {"width": 8.0}}  # fixed ID, rest auto
    }
    ```

### Per-column Options

| Option | Type | Description |
|-------|------|-----------|
| `width` | `float` | Fixed width (override) |
| `min_width` | `float` | Minimum width |
| `max_width` | `float` | Maximum width |

---

## PDF

Generated via **ReportLab** in A4 landscape orientation with a styled table.

```python
spec = ReportSpec(
    output_format="pdf",
    columns=[
        ColumnSpec(label="ID", source="id", type="int"),
        ColumnSpec(label="Name", source="name"),
        ColumnSpec(label="Total", source="total", type="float",
                   formatter=lambda v: f"$ {v:.2f}"),
    ],
)
```

!!! info "PDF Features"
    - **Orientation**: Landscape (A4)
    - **Header**: Blue (#2563EB) with white bold text
    - **Alternating rows**: White / Light Gray (#F1F5F9)
    - **Column width**: Proportional to content (automatic)
    - **Chunked streaming**: Data processed in blocks of 200 rows (configurable)

### Options

| Option | Type | Default | Description |
|-------|------|--------|-----------|
| `chunk_size` | `int` | `200` | Number of rows per chunk. Lower = less RAM, higher = less overhead. |
| `paragraph_threshold` | `int` | `30` | Character limit to use `Paragraph` with automatic line breaks. |

```python
spec = ReportSpec(
    output_format="pdf",
    columns=[...],
    metadata={
        "pdf": {
            "chunk_size": 100,  # less memory per chunk
        }
    },
)
```

!!! warning "Memory Model"
    PDF uses **chunked streaming** — each block of `chunk_size` rows is rendered and 
    discarded before processing the next one. Peak memory is **O(chunk_size × n_columns)**, 
    not O(n). Still, PDF is ~200x slower than CSV/XLSX.
    For datasets over 50K rows, prefer CSV or XLSX.
