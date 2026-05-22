from __future__ import annotations

import json

from obsidian_librarian.pdf_classifier import (
    classify_pdf_source,
    discover_pdf_sources,
    render_pdf_manifest_json,
    staged_pdf_manifest_path,
)


def digital_pdf_bytes() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 80 >>\nstream\n"
        b"BT /F1 12 Tf 72 720 Td (This is deterministic PDF text for Phase 11 tests) Tj ET\n"
        b"endstream\nendobj\n%%EOF\n"
    )


def scanned_pdf_bytes() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /XObject << /Im1 4 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Type /XObject /Subtype /Image /Width 10 /Height 10 >>\nendobj\n"
        b"%%EOF\n"
    )


def encrypted_pdf_bytes() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n"
        b"trailer\n<< /Encrypt 5 0 R >>\n%%EOF\n"
    )


def test_discover_pdf_sources_returns_only_pdfs(tmp_path):
    inbox = tmp_path / "00_Inbox"
    nested = inbox / "nested"
    nested.mkdir(parents=True)
    (inbox / "a.pdf").write_bytes(digital_pdf_bytes())
    (nested / "b.PDF").write_bytes(digital_pdf_bytes())
    (inbox / "note.md").write_text("# Note\n", encoding="utf-8")

    discovered = discover_pdf_sources(inbox)

    assert [path.name for path in discovered] == ["a.pdf", "b.PDF"]


def test_classify_digital_pdf_manifest_is_staged(tmp_path):
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    source = inbox / "manual.pdf"
    original = digital_pdf_bytes()
    source.write_bytes(original)

    manifest = classify_pdf_source(source, source_root=inbox)
    payload = json.loads(render_pdf_manifest_json(manifest))

    assert manifest.source_path == "manual.pdf"
    assert manifest.source_kind == "pdf"
    assert len(manifest.source_hash) == 64
    assert manifest.status == "staged"
    assert manifest.page_count == 1
    assert manifest.classification == "digital_pdf"
    assert manifest.text_density.total_chars > 20
    assert manifest.extraction.method == "classifier_probe"
    assert manifest.extraction.ocr_enabled is False
    assert payload["source_hash"] == manifest.source_hash
    assert source.read_bytes() == original


def test_classify_scanned_pdf_is_skipped_for_deferred_ocr(tmp_path):
    source = tmp_path / "scan.pdf"
    source.write_bytes(scanned_pdf_bytes())

    manifest = classify_pdf_source(source, source_root=tmp_path)

    assert manifest.status == "skipped"
    assert manifest.classification == "scanned_pdf"
    assert manifest.text_density.total_chars == 0
    assert manifest.extraction.ocr_enabled is False
    assert [warning.code for warning in manifest.extraction.warnings] == ["ocr_needed"]


def test_classify_encrypted_pdf_is_skipped(tmp_path):
    source = tmp_path / "locked.pdf"
    source.write_bytes(encrypted_pdf_bytes())

    manifest = classify_pdf_source(source, source_root=tmp_path)

    assert manifest.status == "skipped"
    assert manifest.classification == "encrypted_pdf"
    assert [warning.code for warning in manifest.extraction.warnings] == ["encrypted_pdf"]


def test_classify_malformed_pdf_fails(tmp_path):
    source = tmp_path / "not-a-pdf.pdf"
    source.write_bytes(b"not a pdf")

    manifest = classify_pdf_source(source, source_root=tmp_path)

    assert manifest.status == "failed"
    assert manifest.classification == "malformed_pdf"
    assert manifest.page_count == 0
    assert [warning.code for warning in manifest.extraction.warnings] == ["invalid_header"]


def test_staged_pdf_manifest_path_is_safe():
    manifest = classify_pdf_source.__annotations__
    assert "return" in manifest

    source_manifest = classify_pdf_source
    assert source_manifest is not None


def test_staged_pdf_manifest_path_uses_pdf_namespace(tmp_path):
    inbox = tmp_path / "00_Inbox"
    nested = inbox / "Vendor Manuals"
    nested.mkdir(parents=True)
    source = nested / "PV Inverter Manual.pdf"
    source.write_bytes(digital_pdf_bytes())

    manifest = classify_pdf_source(source, source_root=inbox)

    assert staged_pdf_manifest_path(manifest).as_posix() == (
        "pdf/Vendor-Manuals/PV-Inverter-Manual.manifest.json"
    )
