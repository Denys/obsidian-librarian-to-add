"""Command-line interface for Obsidian Librarian Agent.

Phase 1 intentionally provides only a safe CLI skeleton. Runtime ingestion is added in later
phases after staged-write safety is implemented.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from obsidian_librarian import __version__


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
        help="Placeholder for future Markdown/TXT ingest.",
    )
    ingest.add_argument(
        "inbox",
        nargs="?",
        help="Inbox directory to process in a later phase.",
    )
    ingest.add_argument(
        "--vault",
        help="Vault root path. Runtime behavior is not implemented in Phase 1.",
    )
    ingest.add_argument(
        "--mode",
        choices=("read-only", "draft"),
        default="draft",
        help="Planned action mode. Phase 1 performs no writes.",
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

    print(
        f"Command '{args.command}' is registered, but runtime behavior is not implemented in Phase 1."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
