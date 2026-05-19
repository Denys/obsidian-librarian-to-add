"""Golden eval runner for Obsidian Librarian.

The eval runner uses deterministic filesystem fixtures and does not require network access,
API keys, model calls, or a real Obsidian vault.
"""

from __future__ import annotations

import argparse
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from obsidian_librarian.ingest import ingest_inbox
from obsidian_librarian.validators import validate_path


@dataclass(frozen=True)
class EvalResult:
    """One eval result."""

    case_id: str
    passed: bool
    message: str


EvalCase = Callable[[], EvalResult]


def eval_staging_only_default() -> EvalResult:
    """Draft ingest writes only staged material and preserves raw source."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        inbox = root / "00_Inbox"
        inbox.mkdir()
        source = inbox / "note.md"
        original = "# Note\n\nTODO: check\n"
        source.write_text(original, encoding="utf-8")

        result = ingest_inbox(inbox, root, mode="draft")

        source_note = root / "90_Staging" / "Sources" / "note_md.source.md"
        report = root / "90_Staging" / "review_report.md"
        passed = (
            len(result.generated) == 1
            and source_note.exists()
            and report.exists()
            and source.read_text(encoding="utf-8") == original
        )
        return EvalResult("staging_only_default", passed, "draft ingest staging check")


def eval_read_only_no_writes() -> EvalResult:
    """Read-only ingest must not create staging outputs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        inbox = root / "00_Inbox"
        inbox.mkdir()
        (inbox / "note.txt").write_text("Text", encoding="utf-8")

        result = ingest_inbox(inbox, root, mode="read-only")

        passed = result.generated == [] and not (root / "90_Staging").exists()
        return EvalResult("read_only_no_writes", passed, "read-only write check")


def eval_duplicate_ingest_unique_paths() -> EvalResult:
    """Repeated ingest should create unique files rather than replacing prior outputs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        inbox = root / "00_Inbox"
        inbox.mkdir()
        (inbox / "note.md").write_text("# Note\n", encoding="utf-8")

        ingest_inbox(inbox, root, mode="draft")
        ingest_inbox(inbox, root, mode="draft")

        passed = (
            (root / "90_Staging" / "Sources" / "note_md.source.md").exists()
            and (root / "90_Staging" / "Sources" / "note_md.source_1.md").exists()
            and (root / "90_Staging" / "review_report.md").exists()
            and (root / "90_Staging" / "review_report_1.md").exists()
        )
        return EvalResult("duplicate_ingest_unique_paths", passed, "duplicate path check")


def eval_unsupported_files_reported() -> EvalResult:
    """Unsupported files should appear in the review report."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        inbox = root / "00_Inbox"
        inbox.mkdir()
        (inbox / "note.md").write_text("# Note\n", encoding="utf-8")
        (inbox / "image.png").write_text("not an image", encoding="utf-8")

        ingest_inbox(inbox, root, mode="draft")
        report = (root / "90_Staging" / "review_report.md").read_text(encoding="utf-8")

        passed = "Skipped files: 1" in report and "unsupported extension" in report
        return EvalResult("unsupported_files_reported", passed, "unsupported file report check")


def eval_validation_catches_broken_note() -> EvalResult:
    """Validation should fail for malformed staged Markdown."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        broken = root / "broken.md"
        broken.write_text("# Broken\n", encoding="utf-8")

        summary = validate_path(broken)

        passed = not summary.passed and bool(summary.issues)
        return EvalResult("validation_catches_broken_note", passed, "validator failure check")


EVAL_CASES: tuple[EvalCase, ...] = (
    eval_staging_only_default,
    eval_read_only_no_writes,
    eval_duplicate_ingest_unique_paths,
    eval_unsupported_files_reported,
    eval_validation_catches_broken_note,
)


def run_all_evals() -> list[EvalResult]:
    """Run all golden evals."""
    return [case() for case in EVAL_CASES]


def main(argv: Sequence[str] | None = None) -> int:
    """Run evals from the command line."""
    parser = argparse.ArgumentParser(description="Run Obsidian Librarian golden evals.")
    parser.parse_args(argv)

    results = run_all_evals()
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.case_id}: {result.message}")

    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
