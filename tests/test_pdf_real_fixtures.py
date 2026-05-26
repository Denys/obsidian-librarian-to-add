"""Acceptance tests for copied real PDF fixtures."""

from __future__ import annotations

from pathlib import Path

from obsidian_librarian.pdf_classifier import classify_pdf_source

FIXTURE_ROOT = Path("fixtures/pdf")

FIXTURE_EXPECTATIONS = {
    "digital-basic.pdf": {
        "status": "staged",
        "classifications": {"digital_pdf"},
    },
    "malformed.pdf": {
        "status": "failed",
        "classifications": {"malformed_pdf"},
        "warning": "invalid_header",
    },
    "scanned-one-page.pdf": {
        "status": "skipped",
        "classifications": {"scanned_pdf"},
        "warning": "ocr_needed",
    },
    "pv-inverter-datasheet.pdf": {
        "status": "needs_review",
        "classifications": {"mixed_pdf"},
    },
    "pv-installation-manual-excerpt.pdf": {
        "status": "needs_review",
        "classifications": {"mixed_pdf"},
    },
    "table-heavy-electrical-spec.pdf": {
        "status": "staged",
        "classifications": {"digital_pdf"},
    },
    "app-note-mixed-layout.pdf": {
        "status": "needs_review",
        "classifications": {"mixed_pdf", "digital_pdf"},
    },
}


def test_copied_pdf_fixtures_exist() -> None:
    assert (FIXTURE_ROOT / "fixtures.yaml").is_file()
    for filename in FIXTURE_EXPECTATIONS:
        assert (FIXTURE_ROOT / filename).is_file(), filename


def test_copied_pdf_fixtures_match_classifier_expectations() -> None:
    for filename, expected in FIXTURE_EXPECTATIONS.items():
        manifest = classify_pdf_source(FIXTURE_ROOT / filename, source_root=FIXTURE_ROOT)

        assert manifest.source_path == filename
        assert manifest.source_kind == "pdf"
        assert len(manifest.source_hash) == 64
        assert manifest.status == expected["status"], filename
        assert manifest.classification in expected["classifications"], filename
        assert manifest.extraction.ocr_enabled is False
        if manifest.status != "failed":
            assert manifest.page_count > 0

        expected_warning = expected.get("warning")
        if expected_warning is not None:
            warning_codes = {warning.code for warning in manifest.extraction.warnings}
            assert expected_warning in warning_codes
