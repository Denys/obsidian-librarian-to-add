"""Acceptance tests for copied real PDF fixtures."""

from __future__ import annotations

from pathlib import Path

from obsidian_librarian.pdf_classifier import classify_pdf_source

FIXTURE_ROOT = Path("fixtures/pdf")
ALLOWED_STATUSES = {"staged", "needs_review", "skipped", "failed"}

FIXTURE_FILENAMES = (
    "digital-basic.pdf",
    "malformed.pdf",
    "scanned-one-page.pdf",
    "pv-inverter-datasheet.pdf",
    "pv-installation-manual-excerpt.pdf",
    "table-heavy-electrical-spec.pdf",
    "app-note-mixed-layout.pdf",
    "2 Classification of PV Power Systems - PV PS -- modelling design control.pdf",
    "A comprehensive techno-economic review of microinverters.pdf",
)

EXACT_EXPECTATIONS = {
    "digital-basic.pdf": {
        "status": "staged",
        "classification": "digital_pdf",
    },
    "malformed.pdf": {
        "status": "failed",
        "classification": "malformed_pdf",
        "warning": "invalid_header",
    },
}


def test_copied_pdf_fixtures_exist() -> None:
    assert (FIXTURE_ROOT / "fixtures.yaml").is_file()
    for filename in FIXTURE_FILENAMES:
        assert (FIXTURE_ROOT / filename).is_file(), filename


def test_copied_pdf_fixtures_generate_safe_manifests() -> None:
    for filename in FIXTURE_FILENAMES:
        manifest = classify_pdf_source(FIXTURE_ROOT / filename, source_root=FIXTURE_ROOT)

        assert manifest.source_path == filename
        assert manifest.source_kind == "pdf"
        assert len(manifest.source_hash) == 64
        assert manifest.status in ALLOWED_STATUSES, filename
        assert manifest.classification, filename
        assert manifest.extraction.ocr_enabled is False
        if manifest.status != "failed":
            assert manifest.page_count > 0


def test_deterministic_pdf_fixtures_match_exact_classifier_expectations() -> None:
    for filename, expected in EXACT_EXPECTATIONS.items():
        manifest = classify_pdf_source(FIXTURE_ROOT / filename, source_root=FIXTURE_ROOT)

        assert manifest.status == expected["status"], filename
        assert manifest.classification == expected["classification"], filename

        expected_warning = expected.get("warning")
        if expected_warning is not None:
            warning_codes = {warning.code for warning in manifest.extraction.warnings}
            assert expected_warning in warning_codes


def test_heavy_fixture_entries_present_in_yaml() -> None:
    fixtures_yaml = (FIXTURE_ROOT / "fixtures.yaml").read_text(encoding="utf-8")
    assert "pv_power_systems_classification_chapter" in fixtures_yaml
    assert "microinverter_techno_economic_review" in fixtures_yaml
