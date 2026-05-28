from __future__ import annotations

import argparse
from collections.abc import Sequence

from obsidian_patron import __version__
from obsidian_patron.docling_pipe import ingest_pdf_to_ingestion
from obsidian_patron.propose import generate_proposal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="obsidian-patron", description="Write-capable Obsidian Patron ingestion CLI."
    )
    parser.add_argument("--version", action="version", version=f"obsidian-patron {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    ingest = subparsers.add_parser("ingest", help="Ingest one PDF into 91_Ingestion")
    ingest.add_argument("pdf")
    ingest.add_argument("--vault", required=True)
    ingest.add_argument("--force", action="store_true")
    propose = subparsers.add_parser("propose", help="Generate deterministic proposal for slug")
    propose.add_argument("slug")
    propose.add_argument("--vault", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "ingest":
        try:
            result = ingest_pdf_to_ingestion(args.pdf, args.vault, force=args.force)
        except (FileNotFoundError, FileExistsError, ValueError) as exc:
            print(f"Error: {exc}")
            return 2
        print(f"Ingested: {result.slug}")
        print(f"Output: {result.output_dir}")
        print(f"Manifest: {result.manifest_path}")
        return 0

    if args.command == "propose":
        try:
            proposal = generate_proposal(args.slug, args.vault)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error: {exc}")
            return 2
        print(f"Proposal: {proposal}")
        return 0
    return 0
