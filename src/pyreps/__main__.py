from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .adapters import JsonAdapter, JsonStreamingAdapter
from .contracts import OutputFormat
from .inference import infer_report_spec


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(prog="pyreps", description="PyReps CLI tools")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Infer command
    infer_parser = subparsers.add_parser("infer", help="Infer ReportSpec from a data source")
    infer_parser.add_argument("file", type=str, help="Path to JSON file")
    infer_parser.add_argument(
        "--sample", type=int, default=100, help="Number of records to sample (default: 100)"
    )
    infer_parser.add_argument(
        "--format",
        choices=["csv", "xlsx", "pdf"],
        default="csv",
        help="Target output format (default: csv)",
    )
    infer_parser.add_argument(
        "--stream", action="store_true", help="Use streaming adapter for large files"
    )

    return parser


def handle_infer(args: argparse.Namespace) -> None:
    """Handle the 'infer' command logic."""
    path = Path(args.file)
    if not path.exists():
        print(f"Error: File {path} not found.", file=sys.stderr)
        sys.exit(1)

    if args.stream:
        adapter = JsonStreamingAdapter()
        data_source = path
    else:
        try:
            adapter = JsonAdapter()
            data_source = path.read_bytes()
        except Exception as exc:
            print(f"Error reading file: {exc}", file=sys.stderr)
            sys.exit(1)

    try:
        spec = infer_report_spec(
            adapter=adapter,
            data_source=data_source,
            sample_size=args.sample,
            output_format=args.format,
        )
        # Use the built-in serialization method from the contract
        print(json.dumps(spec.to_dict(), indent=2))
    except Exception as exc:
        print(f"Error during inference: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "infer":
        handle_infer(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
