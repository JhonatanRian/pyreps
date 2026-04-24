# Project Gemini Context: pyreps

## Project Overview
`pyreps` is a high-performance Python library designed for generating reports in CSV, XLSX, and PDF formats. It prioritizes low memory usage through a 100% streaming pipeline for CSV and XLSX, leveraging Rust-powered components (`rustpy-xlsxwriter`, `orjson`) for maximum speed.

### Main Technologies
- **Python 3.12+**: Utilizes modern features like `slots=True` in dataclasses and advanced typing.
- **Rust Integration**: Uses `rustpy-xlsxwriter` for fast XLSX generation and `orjson` for high-speed JSON parsing.
- **ReportLab**: Used for PDF generation.
- **UV**: Modern Python package and project manager.
- **MkDocs**: Documentation site generator with the Material theme.

### Architecture
The project follows a modular pipeline architecture:
1.  **InputAdapters** (`src/py_reports/adapters.py`): Normalize various data sources (`list[dict]`, JSON, SQL) into an iterable of mapping records.
2.  **Mapping & Coercion** (`src/py_reports/mapping.py`, `src/py_reports/coercion.py`): Transform raw records into a normalized format based on a `ReportSpec`, applying type coercion and custom formatters.
3.  **Renderers** (`src/py_reports/renderers.py`): Convert the normalized rows into the final output format.
    - `CsvRenderer`: Uses the Python `csv` standard library.
    - `XlsxRenderer`: Uses `rustpy-xlsxwriter` and custom ZIP-patching for streaming column widths.
    - `PdfRenderer`: Uses `ReportLab` for layout-aware PDF generation.

## Building and Running

### Prerequisites
- Python 3.12 or higher.
- [uv](https://github.com/astral-sh/uv) installed.

### Installation
```bash
uv sync
```

### Running Tests
```bash
uv run pytest
```

### Building Documentation
```bash
uv run mkdocs serve  # Preview
uv run mkdocs build  # Build static site
```

## Development Conventions

### Coding Style
- **Strict Typing**: All functions and classes must use type hints. `Protocol` is used for defining interfaces (`InputAdapter`, `Renderer`).
- **Data Integrity**: Uses frozen dataclasses with `slots=True` for configuration and internal contracts (`ReportSpec`, `ColumnSpec`).
- **Separation of Concerns**: Core logic is decoupled from specific I/O implementations via adapters and renderers.
- **Streaming First**: For CSV and XLSX, always prefer streaming over materializing data in memory. Use generators and iterable processing.

### Testing Practices
- **Unit Testing**: Each component (adapters, mapping, coercion, renderers) has a corresponding test file in the `tests/` directory.
- **Integration Testing**: `test_service.py` covers the end-to-end `generate_report` flow.
- **Tooling**: Uses `pytest` for test execution.

### Project Structure
- `src/py_reports/`: Core source code.
- `tests/`: Comprehensive test suite.
- `docs/`: Markdown-based documentation.
- `benchmarks/`: Performance measurement scripts.
- `pyproject.toml`: Project configuration, dependencies, and build system.
