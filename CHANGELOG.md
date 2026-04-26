# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-04-26

### Added
- Implemented automated report specification inference (`ReportSpec`) from mapping records.
- Added CLI tool for JSON data analysis and specification generation.
- Introduced memory stability testing suite to ensure constant memory usage in streaming pipelines.
- Added comprehensive unit tests for CLI, adapters, and internal utilities.
- New project task documentation and development guides.

### Changed
- Optimized coercion performance for large datasets.
- Implemented row-level error tracking with context enrichment and detailed exception handling.
- Improved type safety across all input adapters and mapping components.
- Refactored internal utilities for database connections and XML/ZIP patching.

## [0.1.5] - 2026-04-24

### Added
- Created `src/pyreps/utils/db.py` to centralize database connection logic and normalize DB-API 2.0 driver inconsistencies (heuristics for closed connections).
- Introduced `src/pyreps/utils/xml_zip.py` to modularize low-level XML patching within ZIP archives, improving the maintainability of the XLSX renderer.
- Added `ensure_mapping_stream` utility in `records.py` to provide optimized, fail-fast stream validation.

### Changed
- Refactored `src/pyreps/adapters.py` to use modular utilities, removing infrastructure code from business logic.
- Refactored `src/pyreps/renderers.py` to delegate file preparation, error wrapping, and record processing to shared utilities.
- Centralized `wrap_render_error` decorator in `src/pyreps/exceptions.py`.
- Moved `prepare_destination` to `src/pyreps/utils/files.py`.
- Improved code legibility in `PdfRenderer` by removing redundant micro-optimization aliases.

### Performance
- Implemented "Validate-First-Row" pattern across all input adapters, eliminating `isinstance` overhead for every record in large datasets.
- Optimized `TupleRecord` with a specialized `.get()` method to bypass the generic `Mapping` lookup overhead.
- Enhanced `WidthTracker` performance by using `enumerate` and localized built-ins in the hot-path loop.

## [0.1.4] - 2026-04-23

### Added
- Parameterized PDF paragraph heuristic with new `paragraph_threshold` option in `PdfRenderOptions`.
- Exported `PdfRenderOptions` in the root `pyreps` package for API consistency.
- Introduced `coerce_int` utility for centralized and robust integer validation in metadata parsing.

### Fixed
- Improved `SqlAdapter` reliability with proactive connection state validation and user-friendly error messages for closed or invalid database connections.
- Resolved a performance regression in XLSX streaming patch by optimizing regex search from $O(N^2)$ to $O(N)$.
- Ensured XLSX patcher robustness against long XML namespaces and chunk boundary edge cases using a safety search overlap.
- Added explicit error handling in XLSX patching, raising `RenderError` instead of producing corrupted files on failure.

### Changed
- Enforced strict architectural immutability for `ReportSpec`:
    - Converted `columns` and `labels` fields from `list` to `tuple`.
    - Wrapped `metadata` in `MappingProxyType` to prevent in-place modifications of the specification.
- Generalized renderer internal APIs to use `Sequence` type hints for better collection flexibility.
- Refactored `SqlAdapter` for better idiomatic compliance and robustness when dealing with diverse DB-API drivers.

### Performance
- Optimized `PdfRenderer` hot-path by replacing row-level generator expressions with `itemgetter` and localized name lookups.
- Improved memory efficiency in XLSX patching using `memoryview` for zero-copy buffer slicing.
- Optimized `SqlAdapter` hot-path by hoisting row-type detection out of the main generator loop.

### Removed
- Deleted obsolete `fix_renderer.py` script.

## [0.1.3] - 2026-04-22

### Added
- `TupleRecord` utility in `src/pyreps/utils/records.py` providing a lightweight `Mapping` wrapper for tuple-based data.

### Performance
- Optimized `SqlAdapter` to use `TupleRecord`, eliminating per-row dictionary allocations (`dict(zip)`) and significantly reducing memory pressure during large-scale SQL data streaming.
- Implemented a Flyweight pattern for database rows, sharing column metadata across all records in a result set.

## [0.1.2] - 2026-04-22

### Fixed
- Improved PDF column width resolution robustness to handle small/empty datasets and prevent layout failures.
- Guaranteed minimum column widths are consistently applied, even when total required width exceeds page capacity.

### Changed
- Refactored renderer width calculation using a new `clamp` utility.
- Optimized PDF width calculation logic using declarative ratio-based redistribution and column-wise max-length processing.
- Moved renderer constants to module level for better performance and maintainability.

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
- Initial release of the `pyreps` core API.
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
