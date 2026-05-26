"""Fixture-backed PDF acceptance tests for classifier, conversion, and sidecars."""

from __future__ import annotations

import json
from pathlib import Path

from obsidian_librarian.ingest import ingest_inbox
from obsidian_librarian.pdf_docling import DoclingAsset, DoclingConversionResult
from obsidian_librarian.validators import validate_path


def digital_pdf_bytes() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 96 >>\nstream\n"
        b"BT /F1 12 Tf 72 720 Td "
        b"(Sentinel-A Sentinel-B deterministic technical PDF text) Tj ET\n"
        b"endstream\nendobj\n%%EOF\n"
    )


def scanned_pdf_bytes() -> bytes:
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


def mixed_pdf_bytes() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R "
        b"/Resources << /XObject << /Im1 5 0 R >> >> >>\n"
        b"endobj\n"
        b"4 0 obj\n<< /Length 90 >>\nstream\n"
        b"BT /F1 12 Tf 72 720 Td "
        b"(Mixed PDF with text and image reference Sentinel-C) Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /XObject /Subtype /Image /Width 10 /Height 10 >>\nendobj\n"
        b"%%EOF\n"
    )


def test_classifier_fixture_acceptance_validates_structural_manifests(
    tmp_path: Path,
) -> None:
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "digital-basic.pdf").write_bytes(digital_pdf_bytes())
    (inbox / "scanned-one-page.pdf").write_bytes(scanned_pdf_bytes())
    (inbox / "mixed-layout.pdf").write_bytes(mixed_pdf_bytes())
    (inbox / "malformed.pdf").write_bytes(b"not a PDF")

    result = ingest_inbox(inbox, tmp_path, mode="draft", include_pdf=True)

    statuses = {manifest.source_path: manifest.status for manifest in result.pdf_manifests}
    classifications = {
        manifest.source_path: manifest.classification for manifest in result.pdf_manifests
    }

    assert statuses["digital-basic.pdf"] == "staged"
    assert classifications["digital-basic.pdf"] == "digital_pdf"
    assert statuses["scanned-one-page.pdf"] == "skipped"
    assert classifications["scanned-one-page.pdf"] == "scanned_pdf"
    assert statuses["mixed-layout.pdf"] == "needs_review"
    assert classifications["mixed-layout.pdf"] == "mixed_pdf"
    assert statuses["malformed.pdf"] == "failed"
    assert classifications["malformed.pdf"] == "malformed_pdf"
    assert all(manifest.extraction.ocr_enabled is False for manifest in result.pdf_manifests)

    validation = validate_path(tmp_path / "90_Staging")

    assert validation.passed is True
    assert len(validation.checked_pdf_manifests) == 4


def test_mocked_docling_acceptance_writes_validated_sidecars_and_assets(
    tmp_path: Path,
) -> None:
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "manual.pdf").write_bytes(digital_pdf_bytes())

    def fake_converter(path: str | Path) -> DoclingConversionResult:
        return DoclingConversionResult(
            markdown="# Converted manual\n\nSentinel-A Sentinel-D",
            structured_json=json.dumps(
                {"pages": 1, "text": "Sentinel-A Sentinel-D"},
                indent=2,
            )
            + "\n",
            engine_version="mock-docling",
            tables_json=json.dumps(
                {
                    "schema_version": 1,
                    "source": "mock",
                    "tables": [{"cells": [["voltage", "current"], ["30V", "5A"]]}],
                },
                indent=2,
            )
            + "\n",
            assets=(
                DoclingAsset(
                    relative_path=Path("figures") / "figure-001.txt",
                    content=b"mock-figure-bytes",
                ),
            ),
        )

    result = ingest_inbox(
        inbox,
        tmp_path,
        mode="draft",
        include_pdf=True,
        pdf_converter="docling",
        pdf_converter_func=fake_converter,
    )

    manifest = result.pdf_manifests[0]
    staging = tmp_path / "90_Staging"
    manifest_path = staging / "pdf" / "manual" / "manifest.json"
    source_note = staging / "pdf" / "manual" / "source.md"
    docling_json = staging / "pdf" / "manual" / "docling.json"
    tables_json = staging / "pdf" / "manual" / "tables.json"
    asset = staging / "pdf" / "manual" / "assets" / "figures" / "figure-001.txt"

    assert manifest.status == "staged"
    assert manifest.extraction.method == "docling"
    assert manifest.outputs.markdown_note == "pdf/manual/source.md"
    assert manifest.outputs.json_sidecar == "pdf/manual/docling.json"
    assert manifest.outputs.table_sidecars == ("pdf/manual/tables.json",)
    assert manifest.outputs.asset_dir == "pdf/manual/assets"
    assert manifest_path.exists()
    assert source_note.exists()
    assert docling_json.exists()
    assert tables_json.exists()
    assert asset.read_bytes() == b"mock-figure-bytes"
    assert "Sentinel-A Sentinel-D" in source_note.read_text(encoding="utf-8")

    validation = validate_path(staging)

    assert validation.passed is True
    assert len(validation.checked_pdf_manifests) == 1
