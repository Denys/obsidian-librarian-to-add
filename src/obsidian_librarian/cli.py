"""Command-line interface for Obsidian Librarian Agent."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from obsidian_librarian import __version__
from obsidian_librarian.ingest import ingest_inbox
from obsidian_librarian.review_report import render_review_report


DESCRIPTION = "Safe deterministic-first Obsidian Librarian CLI."


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="obsidian-librarian",
        description=DESCRIPTION,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"obsidian-librarian {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")

    ingest = subparsers.add_parser(
        "ingest",
        help="Ingest Markdown/TXT files into staged Obsidian notes.",
    )
    ingest.add_argument(
        "inbox",
        help="Inbox directory containing Markdown/TXT source files.",
    )
    ingest.add_argument(
        "--vault",
        required=True,
        help="Vault root path. Staged outputs are written under its 90_Staging directory.",
    )
    ingest.add_argument(
        "--mode",
        choices=("read-only", "draft"),
        default="draft",
        help="Action mode. read-only performs no writes; draft writes staged notes.",
    )

    validate = subparsers.add_parser(
        "validate",
        help="Placeholder for future staged-note validation.",
    )
    validate.add_argument(
        "path",
        nargs="?",
        help="Path to validate in a later phase.",
    )

    report = subparsers.add_parser(
        "report",
        help="Placeholder for future review-report generation.",
    )
    report.add_argument(
        "path",
        nargs="?",
        help="Path to summarize in a later phase.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "ingest":
        return run_ingest_command(args)

    print(
        f"Command '{args.command}' is registered, but runtime behavior is not implemented yet."
    )
    return 0


def run_ingest_command(args: argparse.Namespace) -> int:
    """Run the ingest command and print a compact summary."""
    try:
        result = ingest_inbox(Path(args.inbox), Path(args.vault), mode=args.mode)
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"Error: {exc}")
        return 2

    print(render_review_report(result))
    if result.report_path is not None:
        print(f"\nReview report written to: {result.report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
