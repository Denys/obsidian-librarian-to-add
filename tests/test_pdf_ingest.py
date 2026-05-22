from __future__ import annotations

import json

from obsidian_librarian.cli import main as cli_main
from obsidian_librarian.ingest import ingest_inbox
from obsidian_librarian.pdf_docling import DoclingConversionResult


def digital_pdf_bytes() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 80 >>\nstream\n"
        b"BT /F1 12 Tf 72 720 Td "
        b"(This is deterministic PDF text for Phase 11 tests) Tj ET\n"
        b"endstream\nendobj\n%%EOF\n"
    )


def fake_docling_converter(path):
    return DoclingConversionResult(
        markdown=f"# Converted {path.name}\n\nSentinel-A",
        structured_json='{"docling": true}\n',
        engine_version="test-docling",
    )


def test_pdf_remains_unsupported_without_include_pdf(tmp_path):
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "manual.pdf").write_bytes(digital_pdf_bytes())

    result = ingest_inbox(inbox, tmp_path, mode="read-only")

    assert result.pdf_manifests == []
    assert len(result.skipped) == 1
    assert result.skipped[0].reason == "unsupported extension"
    assert not (tmp_path / "90_Staging").exists()


def test_include_pdf_read_only_classifies_without_writes(tmp_path):
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    source = inbox / "manual.pdf"
    original = digital_pdf_bytes()
    source.write_bytes(original)

    result = ingest_inbox(inbox, tmp_path, mode="read-only", include_pdf=True)

    assert result.skipped == []
    assert len(result.pdf_manifests) == 1
    assert result.pdf_manifests[0].schema_version == 1
    assert result.pdf_manifests[0].classification == "digital_pdf"
    assert result.pdf_manifest_paths == []
    assert source.read_bytes() == original
    assert not (tmp_path / "90_Staging").exists()


def test_include_pdf_draft_writes_manifest_and_report_only(tmp_path):
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "manual.pdf").write_bytes(digital_pdf_bytes())

    result = ingest_inbox(inbox, tmp_path, mode="draft", include_pdf=True)

    manifest_path = tmp_path / "90_Staging" / "pdf" / "manual" / "manifest.json"
    report_path = tmp_path / "90_Staging" / "review_report.md"
    assert result.generated == []
    assert len(result.pdf_manifests) == 1
    assert result.pdf_manifest_paths == [manifest_path]
    assert manifest_path.exists()
    assert report_path.exists()

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")
    assert manifest_payload["schema_version"] == 1
    assert manifest_payload["source_kind"] == "pdf"
    assert manifest_payload["classification"] == "digital_pdf"
    assert manifest_payload["outputs"]["root"] == "pdf/manual"
    assert manifest_payload["extraction"]["method"] == "classifier_probe"
    assert "PDF manifests: 1" in report
    assert "No notes generated." in report
    assert "no PDF Markdown conversion or OCR was run" in report


def test_include_pdf_docling_writes_markdown_json_and_manifest(tmp_path):
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "manual.pdf").write_bytes(digital_pdf_bytes())

    result = ingest_inbox(
        inbox,
        tmp_path,
        mode="draft",
        include_pdf=True,
        pdf_converter="docling",
        pdf_converter_func=fake_docling_converter,
    )

    root = tmp_path / "90_Staging" / "pdf" / "manual"
    manifest_path = root / "manifest.json"
    markdown_path = root / "source.md"
    json_path = root / "docling.json"
    assert manifest_path.exists()
    assert markdown_path.exists()
    assert json_path.exists()
    assert len(result.generated) == 1

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert manifest_payload["extraction"]["method"] == "docling"
    assert manifest_payload["extraction"]["ocr_enabled"] is False
    assert manifest_payload["outputs"]["root"] == "pdf/manual"
    assert manifest_payload["outputs"]["markdown_note"] == "pdf/manual/source.md"
    assert manifest_payload["outputs"]["json_sidecar"] == "pdf/manual/docling.json"
    assert "# Converted manual.pdf" in markdown
    assert "extraction_method: \"docling\"" in markdown


def test_pdf_converter_requires_include_pdf(tmp_path):
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()

    try:
        ingest_inbox(inbox, tmp_path, mode="read-only", pdf_converter="docling")
    except ValueError as exc:
        assert "requires --include-pdf" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_cli_include_pdf_flag_writes_manifest(tmp_path):
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "manual.pdf").write_bytes(digital_pdf_bytes())

    exit_code = cli_main(
        [
            "ingest",
            str(inbox),
            "--vault",
            str(tmp_path),
            "--mode",
            "draft",
            "--include-pdf",
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "90_Staging" / "pdf" / "manual" / "manifest.json").exists()
