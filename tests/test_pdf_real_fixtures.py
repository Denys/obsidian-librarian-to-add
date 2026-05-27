"""Acceptance tests for optional copied real PDF fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

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


def _missing_fixture_files(filenames: tuple[str, ...] = FIXTURE_FILENAMES) -> list[str]:
    return [filename for filename in filenames if not (FIXTURE_ROOT / filename).is_file()]


def _skip_if_optional_pdf_fixtures_missing(filenames: tuple[str, ...] = FIXTURE_FILENAMES) -> None:
    missing = _missing_fixture_files(filenames)
    if missing:
        pytest.skip("optional copied PDF fixture files missing: " + ", ".join(missing))


def test_fixture_inventory_exists() -> None:
    assert (FIXTURE_ROOT / "fixtures.yaml").is_file()


def test_copied_pdf_fixtures_exist_when_available() -> None:
    _skip_if_optional_pdf_fixtures_missing()


@pytest.mark.optional_pdf_fixtures
def test_copied_pdf_fixtures_generate_safe_manifests() -> None:
    _skip_if_optional_pdf_fixtures_missing()
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


@pytest.mark.optional_pdf_fixtures
def test_deterministic_pdf_fixtures_match_exact_classifier_expectations() -> None:
    filenames = tuple(EXACT_EXPECTATIONS)
    _skip_if_optional_pdf_fixtures_missing(filenames)
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
