# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-04-22

### Changed
- Refactored `map_records` to use a "Column Processor" pattern with `NamedTuple`, improving code clarity and maintainability.
- Consolidated coercion error handling by reusing specialized closures.

### Performance
- Optimized the mapping hot-path by pre-calculating column processors outside the record loop.
- Implemented a fast-path for flat dictionary keys, using native `dict.get` in C and bypassing function call overhead.
- Reduced bytecode operations in the main loop by localizing global references and grouping conditional checks.

## [0.1.0] - 2026-04-22

### Added
- Initial release of the `py-reports` core API.
- Support for multiple output formats: **CSV**, **XLSX**, and **PDF**.
- Input adapters for diverse data sources:
    - `ListAdapter`: For standard Python list of dictionaries.
    - `JsonAdapter`: For JSON files (with `orjson` support).
    - `SqlAdapter`: Compatible with DB-API 2.0 (decoupled from specific engines).
    - `JsonStreamingAdapter`: Support for large JSON files using `ijson`.
- Declarative column definitions with automatic type coercion.
- Comprehensive documentation using MkDocs Material theme.
- Report generation logging and transactional cleanup on failure.
- Sheet name validation for XLSX reports and immutable column options.

### Fixed
- Addressed code review feedback on `SqlAdapter` and `PdfRenderer` for better consistency.
- Fixed thread-safety issues in coercion logic by implementing a per-report scoped cache for formatters.
- Improved error handling and validation across all input adapters.

### Changed
- Refactored `SqlAdapter` to use a generic DB-API 2.0 Protocol instead of being tied to SQLite.
- Consolidated coercion logic into specialized utility modules.
- Enhanced XLSX renderer with improved column injection and width tracking.
- Optimized column mapping using pre-split paths for faster nested data access.

### Performance
- Implemented a 100% streaming pipeline to maintain a low memory footprint.
- Integrated Rust-powered `orjson` for high-speed JSON parsing.
- Minimized RAM usage in all renderers by avoiding full data materialization.
- Added streaming ZIP patching for XLSX files to support dynamic column widths without full rewrites.
- Implemented memory-efficient streaming PDF generation using custom `DocTemplate` and chunked flowables.
- Added configurable chunking for PDF rendering to balance speed and memory usage.
