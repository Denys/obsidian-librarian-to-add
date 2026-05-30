from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from obsidian_patron import __version__
from obsidian_patron.docling_pipe import ingest_pdf_to_ingestion
from obsidian_patron.linker import link_ingested_notes
from obsidian_patron.promotion import promote_to_staging, promote_to_trusted, unpromote
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
    propose.add_argument("--allow-new-tags", action="store_true")
    propose.add_argument("--llm", action="store_true")
    propose.add_argument("--model", default="gpt-5.4-mini")
    link = subparsers.add_parser(
        "link", help="Insert matched wikilinks and report unmatched candidates"
    )
    link.add_argument("slug")
    link.add_argument("--vault", required=True)
    unmatched = subparsers.add_parser("unmatched", help="Print unmatched candidates report")
    unmatched.add_argument("slug")
    unmatched.add_argument("--vault", required=True)
    status = subparsers.add_parser("status", help="Show current location and provenance for slug")
    status.add_argument("slug")
    status.add_argument("--vault", required=True)
    promote = subparsers.add_parser("promote", help="Promote an ingestion slug")
    promote.add_argument("slug")
    promote.add_argument("--vault", required=True)
    target = promote.add_mutually_exclusive_group(required=True)
    target.add_argument("--to-staging", action="store_true")
    target.add_argument("--to-trusted", action="store_true")
    promote.add_argument("--hub")
    promote.add_argument("--override", action="store_true")
    unpromote_parser = subparsers.add_parser("unpromote", help="Reverse a recorded promotion")
    unpromote_parser.add_argument("slug")
    unpromote_parser.add_argument("--vault", required=True)
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
            proposal = generate_proposal(
                args.slug,
                args.vault,
                allow_new_tags=args.allow_new_tags,
                use_llm=args.llm,
                model=args.model,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error: {exc}")
            return 2
        print(f"Proposal: {proposal}")
        return 0

    if args.command == "link":
        try:
            result = link_ingested_notes(args.slug, args.vault)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error: {exc}")
            return 2
        print(f"Linked files: {len(result.linked_files)}")
        print(f"Matched candidates: {result.matched_count}")
        print(f"Unmatched candidates: {result.unmatched_count}")
        print(f"Unmatched report: {result.unmatched_report}")
        return 0

    if args.command == "unmatched":
        try:
            report = _unmatched_report_path(args.slug, args.vault)
        except FileNotFoundError as exc:
            print(f"Error: {exc}")
            return 2
        print(report.read_text(encoding="utf-8"), end="")
        return 0

    if args.command == "status":
        try:
            print(_render_status(args.slug, args.vault))
        except FileNotFoundError as exc:
            print(f"Error: {exc}")
            return 2
        return 0

    if args.command == "promote":
        try:
            if args.to_staging:
                result = promote_to_staging(args.slug, args.vault)
            else:
                if not args.hub:
                    print("Error: --hub is required with --to-trusted")
                    return 2
                result = promote_to_trusted(
                    args.slug, args.vault, hub=args.hub, override=args.override
                )
        except (FileNotFoundError, FileExistsError, ValueError) as exc:
            print(f"Error: {exc}")
            return 2
        print(f"Promoted to: {result.promoted_to}")
        print(f"Source: {result.source}")
        print(f"Destination: {result.destination}")
        print(f"Ledger: {result.ledger_path}")
        return 0

    if args.command == "unpromote":
        try:
            result = unpromote(args.slug, args.vault)
        except (FileNotFoundError, FileExistsError, ValueError) as exc:
            print(f"Error: {exc}")
            return 2
        print(f"Unpromoted from: {result.source}")
        print(f"Restored to: {result.destination}")
        print(f"Ledger: {result.ledger_path}")
        return 0
    return 0


def _unmatched_report_path(slug: str, vault_root: str | Path) -> Path:
    slug_dir = _find_slug_dir(slug, vault_root)
    report = slug_dir / "_unmatched_candidates.md"
    if not report.exists():
        raise FileNotFoundError(f"Unmatched candidates report not found: {report}")
    return report


def _render_status(slug: str, vault_root: str | Path) -> str:
    slug_dir = _find_slug_dir(slug, vault_root)
    manifest = slug_dir / "_ingest_manifest.json"
    proposal = slug_dir / "_proposal.md"
    ledger = slug_dir / "_promotion.json"
    lines = [
        f"Slug: {slug}",
        f"Location: {slug_dir}",
        f"Manifest: {manifest if manifest.exists() else 'missing'}",
        f"Proposal: {proposal if proposal.exists() else 'missing'}",
        f"Promotion ledger: {ledger if ledger.exists() else 'missing'}",
    ]
    return "\n".join(lines)


def _find_slug_dir(slug: str, vault_root: str | Path) -> Path:
    vault = Path(vault_root).expanduser().resolve(strict=False)
    candidates = [
        vault / "91_Ingestion" / slug,
        vault / "90_Staging" / slug,
    ]
    candidates.extend(sorted(path for path in vault.glob(f"*/{slug}") if path.is_dir()))
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        if resolved.exists() and resolved.is_dir():
            return resolved
    raise FileNotFoundError(f"Slug not found: {slug}")


if __name__ == "__main__":
    raise SystemExit(main())
