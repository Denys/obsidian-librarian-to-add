# ruff: noqa: E402
"""Golden eval runner for Obsidian Librarian.

The eval runner uses deterministic filesystem fixtures and does not require network access,
API keys, model calls, or a real Obsidian vault.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
from collections.abc import Callable, Sequence
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from obsidian_librarian.cli import main as cli_main
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


def pdf_digital_fixture() -> bytes:
    """Return a tiny local digital-PDF-like fixture for deterministic tests/evals."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 80 >>\nstream\n"
        b"BT /F1 12 Tf 72 720 Td "
        b"(This is deterministic PDF text for Phase 11 evals) Tj ET\n"
        b"endstream\nendobj\n%%EOF\n"
    )


def pdf_scanned_fixture() -> bytes:
    """Return a tiny image-only PDF-like fixture for OCR-deferred evals."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R "
        b"/Resources << /XObject << /Im1 4 0 R >> >> >>\n"
        b"endobj\n"
        b"4 0 obj\n<< /Type /XObject /Subtype /Image /Width 10 /Height 10 >>\nendobj\n"
        b"%%EOF\n"
    )


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


def eval_review_quality_cli_missing_source_blocking() -> EvalResult:
    """CLI review-quality should return blocking exit code for missing source_path."""
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

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cli_main(["review-quality", str(note)])

        rendered = output.getvalue()
        passed = (
            exit_code == 1
            and "# Obsidian Librarian Note Quality Review" in rendered
            and "Verdict: fail" in rendered
        )
        return EvalResult(
            "review_quality_cli_missing_source_blocking",
            passed,
            "review-quality CLI blocking exit-code check",
        )


def eval_enrich_mock_success() -> EvalResult:
    """Mock enrichment should succeed in draft mode with staged output."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        inbox = root / "00_Inbox"
        inbox.mkdir()
        (inbox / "note.md").write_text("# Note\n", encoding="utf-8")
        ingest_inbox(inbox, root, mode="draft")

        exit_code = cli_main(
            [
                "enrich",
                str(root / "90_Staging"),
                "--vault",
                str(root),
                "--mode",
                "draft",
                "--extractor",
                "mock",
            ]
        )
        passed = exit_code == 0 and any((root / "90_Staging" / "Enriched").glob("*.md"))
        return EvalResult("enrich_mock_success", passed, "mock enrich success check")


def eval_pdf_disabled_by_default() -> EvalResult:
    """PDFs should remain unsupported unless explicitly enabled."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        inbox = root / "00_Inbox"
        inbox.mkdir()
        (inbox / "manual.pdf").write_bytes(pdf_digital_fixture())

        result = ingest_inbox(inbox, root, mode="read-only")

        passed = (
            result.pdf_manifests == []
            and len(result.skipped) == 1
            and result.skipped[0].reason == "unsupported extension"
            and not (root / "90_Staging").exists()
        )
        return EvalResult("pdf_disabled_by_default", passed, "PDF disabled-by-default check")


def eval_pdf_read_only_manifest_no_writes() -> EvalResult:
    """Read-only PDF intake should classify without writes or source mutation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        inbox = root / "00_Inbox"
        inbox.mkdir()
        source = inbox / "manual.pdf"
        original = pdf_digital_fixture()
        source.write_bytes(original)

        result = ingest_inbox(inbox, root, mode="read-only", include_pdf=True)

        passed = (
            len(result.pdf_manifests) == 1
            and result.pdf_manifests[0].classification == "digital_pdf"
            and result.pdf_manifest_paths == []
            and source.read_bytes() == original
            and not (root / "90_Staging").exists()
        )
        return EvalResult(
            "pdf_read_only_manifest_no_writes",
            passed,
            "PDF read-only classifier no-write check",
        )


def eval_pdf_draft_manifest_written() -> EvalResult:
    """Draft PDF intake should write manifest JSON but no converted source note."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        inbox = root / "00_Inbox"
        inbox.mkdir()
        (inbox / "manual.pdf").write_bytes(pdf_digital_fixture())

        result = ingest_inbox(inbox, root, mode="draft", include_pdf=True)
        manifest_path = root / "90_Staging" / "pdf" / "manual.manifest.json"
        report_path = root / "90_Staging" / "review_report.md"
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        report = report_path.read_text(encoding="utf-8")

        passed = (
            result.generated == []
            and len(result.pdf_manifests) == 1
            and manifest_path.exists()
            and payload["classification"] == "digital_pdf"
            and payload["extraction"]["method"] == "classifier_probe"
            and "PDF manifests: 1" in report
            and "No notes generated." in report
        )
        return EvalResult("pdf_draft_manifest_written", passed, "PDF draft manifest write check")


def eval_pdf_scanned_deferred_ocr() -> EvalResult:
    """Image-only PDFs should be classified as OCR-deferred."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        inbox = root / "00_Inbox"
        inbox.mkdir()
        (inbox / "scan.pdf").write_bytes(pdf_scanned_fixture())

        result = ingest_inbox(inbox, root, mode="read-only", include_pdf=True)
        manifest = result.pdf_manifests[0]

        passed = (
            manifest.classification == "scanned_pdf"
            and manifest.status == "skipped"
            and manifest.extraction.ocr_enabled is False
            and [warning.code for warning in manifest.extraction.warnings] == ["ocr_needed"]
        )
        return EvalResult("pdf_scanned_deferred_ocr", passed, "PDF OCR-deferred check")


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
    eval_review_quality_cli_missing_source_blocking,
    eval_enrich_mock_success,
    eval_pdf_disabled_by_default,
    eval_pdf_read_only_manifest_no_writes,
    eval_pdf_draft_manifest_written,
    eval_pdf_scanned_deferred_ocr,
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
