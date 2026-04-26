# Performance

**{{ project_name }}** is designed for high performance and low memory consumption.

## Streaming Pipeline

The entire pipeline is **lazy** — data flows record by record without accumulating in memory:

```mermaid
graph LR
    A["Adapter<br/><i>yield record</i>"] --> B["Mapping<br/><i>yield row</i>"]
    B --> C["Renderer<br/><i>write row</i>"]

    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#e8f5e9
```

Each component is a Python **generator**. Data enters, is processed, and leaves — with no intermediate lists.

## Benchmarks

Results with 6 columns, declarative types enabled:

| Format | Records | Time | Peak RAM | File | rows/s |
|---------|-----------|-------|----------|---------|--------|
| CSV | 10K | 0.05s | **51.11 MB** | 0.63 MB | 194K |
| CSV | 100K | 0.50s | **51.11 MB** | 6.67 MB | 201K |
| CSV | 500K | 2.39s | **51.11 MB** | 34.9 MB | 209K |
| XLSX | 10K | 0.13s | **51.11 MB** | 0.34 MB | 76K |
| XLSX | 100K | 0.90s | **51.11 MB** | 3.25 MB | 111K |
| XLSX | 500K | 4.37s | **51.11 MB** | 16.0 MB | 114K |
| PDF | 10K | 1.74s | 51.11 MB | 1.01 MB | 5K |

!!! success "Stable Memory (CSV/XLSX)"
    CSV and XLSX maintain stable memory usage (~51MB process baseline) regardless of the data volume.

!!! info "PDF: Memory O(chunk_size)"
    The PDF uses streaming by 200-row chunks (configurable). Peak RAM is proportional to `chunk_size × n_columns`. See [Formats → PDF](formats.md#pdf) for details.

## Performance Stack

| Component | Library | Language | Why |
|-----------|-----|-----------|---------|
| JSON parsing | `orjson` | **Rust** | ~6x faster than `json` stdlib |
| XLSX writing | `{{ rust_lib }}` | **Rust** | Native writing, accepts generators |
| XLSX widths | ZIP streaming | **Python** | Patching in 64KB chunks, no DOM |
| CSV | `csv` stdlib | **C** | Native module, as fast as possible |
| PDF | `reportlab` | **Python + C** | C core, industry standard |

## Optimization Tips

### Use generators as data source

```python
# ❌ Materializes everything before starting
data = [row for row in fetch_all_rows()]
generate_report(data_source=data, ...)

# ✅ Streaming — constant memory
def stream():
    for page in paginate():
        yield from page
generate_report(data_source=stream(), ...)
```

### Prefer CSV/XLSX for large volumes

PDF processes data in 200-row chunks (configurable via `metadata["pdf"]["chunk_size"]`), keeping memory proportional to the chunk size — not to the total records. Even so, the speed (~165 rows/s) is much lower than CSV/XLSX. For datasets above 50K rows, prefer CSV or XLSX.

### XLSX — `manual` mode for maximum speed

The `auto`/`mixed` mode calculates widths during streaming (minimal overhead). If you don't need automatic width:

```python
metadata={"xlsx": {"width_mode": "manual", "default_width": 15.0}}
```

## Reproducing Benchmarks

```bash
uv run python benchmarks/bench_performance.py
```
