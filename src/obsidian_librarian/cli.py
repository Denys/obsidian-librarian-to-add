"""Command-line interface for Obsidian Librarian Agent."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from obsidian_inventory import VALID_SCOPES
from obsidian_librarian import __version__
from obsidian_librarian.enrich import enrich_path
from obsidian_librarian.extractors import MockExtractor, OpenAIExtractor
from obsidian_librarian.indexer import build_index
from obsidian_librarian.ingest import ingest_inbox
from obsidian_librarian.note_quality import review_note_quality_path
from obsidian_librarian.review_report import render_review_report
from obsidian_librarian.search import search_index
from obsidian_librarian.validators import render_validation_summary, validate_path

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
    ingest.add_argument(
        "--include-pdf",
        action="store_true",
        help="Discover PDFs and write classifier manifests.",
    )
    ingest.add_argument(
        "--pdf-converter",
        choices=("none", "docling"),
        default="none",
        help="Optional PDF converter. docling requires installing the [pdf] extra.",
    )
    ingest.add_argument(
        "--pdf-ocr",
        action="store_true",
        help=(
            "Explicitly enable OCR for scanned PDFs. Requires --include-pdf and "
            "--pdf-converter docling."
        ),
    )

    validate = subparsers.add_parser(
        "validate",
        help="Validate staged Markdown notes.",
    )
    validate.add_argument(
        "path",
        help="Markdown file or directory to validate.",
    )

    review_quality = subparsers.add_parser(
        "review-quality",
        help="Run deterministic note-quality checks for staged Markdown notes.",
    )
    review_quality.add_argument(
        "path",
        help="Markdown file or directory to review.",
    )

    enrich = subparsers.add_parser(
        "enrich",
        help="Optionally enrich staged Markdown notes with deterministic mock or OpenAI extractor.",
    )
    enrich.add_argument("path", help="Staged Markdown file or directory to enrich.")
    enrich.add_argument("--vault", default=".", help="Vault root path.")
    enrich.add_argument("--mode", choices=("read-only", "draft"), default="read-only")
    enrich.add_argument("--extractor", choices=("mock", "openai"), default="mock")
    enrich.add_argument("--model", default="gpt-5.4-mini")

    index = subparsers.add_parser("index", help="Build deterministic read-only vault index.")
    index.add_argument("--vault", default=".", help="Vault root path.")
    index.add_argument(
        "--scope",
        choices=VALID_SCOPES,
        default="vault",
        help="Search/index scope.",
    )

    search = subparsers.add_parser("search", help="Search deterministic vault index.")
    search.add_argument("query", help="Search query")
    search.add_argument("--vault", default=".", help="Vault root path.")
    search.add_argument(
        "--scope",
        choices=VALID_SCOPES,
        default="vault",
        help="Search scope.",
    )

    report = subparsers.add_parser(
        "report",
        help="Placeholder for future review-report inspection.",
    )
    report.add_argument(
        "path",
        nargs="?",
        help="Path to summarize in a later phase.",
    )

    gui = subparsers.add_parser(
        "gui",
        help="Launch the local browser GUI.",
    )
    gui.add_argument("--vault", default=".", help="Default vault root path.")
    gui.add_argument("--host", default="127.0.0.1", help="Bind host.")
    gui.add_argument(
        "--port",
        type=int,
        default=0,
        help="Bind port. Use 0 for a random port.",
    )
    gui.add_argument(
        "--no-browser",
        action="store_true",
        help="Print URL without opening a browser.",
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

    if args.command == "validate":
        return run_validate_command(args)

    if args.command == "review-quality":
        return run_review_quality_command(args)

    if args.command == "enrich":
        return run_enrich_command(args)

    if args.command == "index":
        return run_index_command(args)

    if args.command == "search":
        return run_search_command(args)

    if args.command == "gui":
        return run_gui_command(args)

    print(f"Command '{args.command}' is registered, but runtime behavior is not implemented yet.")
    return 0


def run_ingest_command(args: argparse.Namespace) -> int:
    """Run the ingest command and print a compact summary."""
    try:
        result = ingest_inbox(
            Path(args.inbox),
            Path(args.vault),
            mode=args.mode,
            include_pdf=args.include_pdf,
            pdf_converter=args.pdf_converter,
            pdf_ocr=args.pdf_ocr,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"Error: {exc}")
        return 2

    print(render_review_report(result))
    if result.report_path is not None:
        print(f"\nReview report written to: {result.report_path}")
    return 0


def run_validate_command(args: argparse.Namespace) -> int:
    """Run the validate command."""
    try:
        summary = validate_path(Path(args.path))
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 2

    print(render_validation_summary(summary))
    return 0 if summary.passed else 1


def run_review_quality_command(args: argparse.Namespace) -> int:
    """Run deterministic note-quality review for a file or directory."""
    path = Path(args.path)
    if path.is_file() and path.suffix.lower() != ".md":
        print(f"Error: review-quality only supports Markdown files, got: {path}")
        return 2

    try:
        summary = review_note_quality_path(path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 2

    if not summary.checked_files:
        print(f"Error: no Markdown notes found to review under: {summary.root}")
        return 2

    blocking_count = len(summary.blocking_findings)
    suggestion_count = len(summary.suggestions)
    if blocking_count:
        verdict = "fail"
    elif suggestion_count:
        verdict = "pass with suggestions"
    else:
        verdict = "pass"

    print("# Obsidian Librarian Note Quality Review")
    print(f"Verdict: {verdict}")
    print(f"Checked files: {len(summary.checked_files)}")
    print(f"Blocking findings: {blocking_count}")
    print(f"Suggestions: {suggestion_count}")
    print(f"Skipped files: {len(summary.skipped_files)}")

    if blocking_count:
        print("\n## Blocking findings")
        for finding in summary.blocking_findings:
            print(f"- {finding.path} - {finding.message}")
    else:
        print("\n## Blocking findings")
        print("- None")

    if suggestion_count:
        print("\n## Suggestions")
        for suggestion in summary.suggestions:
            print(f"- {suggestion.path} - {suggestion.message}")
    else:
        print("\n## Suggestions")
        print("- None")

    if summary.skipped_files:
        print("\n## Skipped files")
        for skipped in summary.skipped_files:
            print(f"- {skipped}")

    return 1 if blocking_count else 0


def run_enrich_command(args: argparse.Namespace) -> int:
    """Run optional staged-note enrichment command."""
    extractor = MockExtractor() if args.extractor == "mock" else OpenAIExtractor(model=args.model)

    try:
        summary = enrich_path(
            Path(args.path),
            vault_root=Path(args.vault),
            mode=args.mode,
            extractor=extractor,
            model=args.model if args.extractor == "openai" else None,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 2

    print("# Obsidian Librarian Enrichment")
    print(f"Extractor: {summary.extractor}")
    print(f"Mode: {summary.mode}")
    print(f"Checked files: {len(summary.checked_files)}")
    print(f"Skipped files: {len(summary.skipped_files)}")
    print(f"Outputs: {len(summary.outputs)}")
    print(f"Failures: {len(summary.failures)}")

    if summary.failures:
        print("\n## Failures")
        for failure in summary.failures:
            print(f"- {failure.source_path} - {failure.message}")
        return 1

    return 0


def run_index_command(args: argparse.Namespace) -> int:
    try:
        summary = build_index(Path(args.vault), args.scope)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 2

    print("# Obsidian Librarian Index")
    print(f"Scope: {summary.scope}")
    print(f"Scanned files: {summary.scanned_files}")
    print(f"Indexed records: {len(summary.indexed_records)}")
    return 0


def run_search_command(args: argparse.Namespace) -> int:
    try:
        index = build_index(Path(args.vault), args.scope)
        summary = search_index(index.indexed_records, args.query, args.scope)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 2

    print("# Obsidian Librarian Search")
    print(f"Query: {summary.query}")
    print(f"Scope: {summary.scope}")
    print(f"Searched files: {summary.searched_files}")
    print(f"Matched files: {summary.matched_files}")
    for hit in summary.hits[:20]:
        fields = ",".join(hit.matched_fields)
        print(f"- {hit.path} (scope={hit.scope}, score={hit.score}, fields={fields})")
    return 0


def run_gui_command(args: argparse.Namespace) -> int:
    """Run the local browser GUI with a lazy import."""
    from obsidian_librarian.gui.server import run_gui

    return run_gui(
        vault=args.vault,
        host=args.host,
        port=args.port,
        no_browser=args.no_browser,
    )


if __name__ == "__main__":
    raise SystemExit(main())
