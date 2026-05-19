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
from obsidian_librarian.note_quality import review_note_quality
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


def eval_source_note_requires_source_path() -> EvalResult:
    """Generated source notes should preserve source_path provenance."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        inbox = root / "00_Inbox"
        inbox.mkdir()
        (inbox / "note.md").write_text("# Note\n", encoding="utf-8")

        ingest_inbox(inbox, root, mode="draft")
        source_note = root / "90_Staging" / "Sources" / "note_md.source.md"
        content = source_note.read_text(encoding="utf-8")

        passed = 'source_path: "note.md"' in content
        return EvalResult(
            "source_note_requires_source_path",
            passed,
            "source note provenance check",
        )


def eval_generated_note_requires_staged_status() -> EvalResult:
    """Generated source notes should remain staged for review."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        inbox = root / "00_Inbox"
        inbox.mkdir()
        (inbox / "note.md").write_text("# Note\n", encoding="utf-8")

        ingest_inbox(inbox, root, mode="draft")
        source_note = root / "90_Staging" / "Sources" / "note_md.source.md"
        content = source_note.read_text(encoding="utf-8")

        passed = 'status: "staged"' in content
        return EvalResult(
            "generated_note_requires_staged_status",
            passed,
            "staged status check",
        )


def eval_action_items_separated_from_claims() -> EvalResult:
    """Action-like content should appear under Action items, not only Key claims."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        inbox = root / "00_Inbox"
        inbox.mkdir()
        (inbox / "note.md").write_text("# Note\n\nTODO: call Sam\n", encoding="utf-8")

        ingest_inbox(inbox, root, mode="draft")
        source_note = root / "90_Staging" / "Sources" / "note_md.source.md"
        content = source_note.read_text(encoding="utf-8")
        result = review_note_quality(source_note)

        passed = (
            "TODO: call Sam" in content
            and "## Action items" in content
            and not any(
                finding.check_id == "action_items_in_key_claims"
                for finding in result.blocking_findings
            )
        )
        return EvalResult(
            "action_items_separated_from_claims",
            passed,
            "action separation check",
        )


def eval_deterministic_summary_not_overclaimed() -> EvalResult:
    """Deterministic source-note placeholders should stay honest."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        inbox = root / "00_Inbox"
        inbox.mkdir()
        (inbox / "note.md").write_text("# Note\n", encoding="utf-8")

        ingest_inbox(inbox, root, mode="draft")
        source_note = root / "90_Staging" / "Sources" / "note_md.source.md"
        content = source_note.read_text(encoding="utf-8")
        result = review_note_quality(source_note)

        passed = (
            "No deterministic summary generated" in content
            and not any(
                finding.check_id == "summary_overclaims_semantic_extraction"
                for finding in result.blocking_findings
            )
        )
        return EvalResult(
            "deterministic_summary_not_overclaimed",
            passed,
            "deterministic summary honesty check",
        )


def eval_note_quality_missing_source_is_blocking() -> EvalResult:
    """Missing provenance should be a blocking note-quality finding."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        note = root / "missing_source.md"
        note.write_text(
            "---\n"
            'type: "source"\n'
            'status: "staged"\n'
            "---\n\n"
            "# Missing Source\n\n"
            "## Summary\n\n"
            "No deterministic summary generated in Phase 3.\n\n"
            "## Key claims\n\n"
            "No key claims extracted deterministically in Phase 3.\n\n"
            "## Action items\n\n"
            "No action items extracted deterministically.\n\n"
            "## Open questions\n\n"
            "No open questions extracted deterministically in Phase 3.\n\n"
            "## Links\n\n",
            encoding="utf-8",
        )

        result = review_note_quality(note)
        passed = any(
            finding.check_id == "missing_source_path"
            for finding in result.blocking_findings
        )
        return EvalResult(
            "note_quality_missing_source_is_blocking",
            passed,
            "missing source quality check",
        )


def eval_note_quality_links_are_suggestions() -> EvalResult:
    """Missing wikilinks should remain suggestions rather than hard failures."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        inbox = root / "00_Inbox"
        inbox.mkdir()
        (inbox / "note.md").write_text("# Note\n", encoding="utf-8")

        ingest_inbox(inbox, root, mode="draft")
        source_note = root / "90_Staging" / "Sources" / "note_md.source.md"
        result = review_note_quality(source_note)

        passed = result.passed and any(
            suggestion.check_id == "missing_wikilinks" for suggestion in result.suggestions
        )
        return EvalResult(
            "note_quality_links_are_suggestions",
            passed,
            "link suggestion quality check",
        )


EVAL_CASES: tuple[EvalCase, ...] = (
    eval_staging_only_default,
    eval_read_only_no_writes,
    eval_duplicate_ingest_unique_paths,
    eval_unsupported_files_reported,
    eval_validation_catches_broken_note,
    eval_source_note_requires_source_path,
    eval_generated_note_requires_staged_status,
    eval_action_items_separated_from_claims,
    eval_deterministic_summary_not_overclaimed,
    eval_note_quality_missing_source_is_blocking,
    eval_note_quality_links_are_suggestions,
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
