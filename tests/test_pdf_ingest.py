from __future__ import annotations

import json

import pytest

from obsidian_librarian.cli import main as cli_main
from obsidian_librarian.ingest import ingest_inbox
from obsidian_librarian.models import IngestRunResult
from obsidian_librarian.note_quality import review_note_quality
from obsidian_librarian.pdf_docling import DoclingConversionResult
from obsidian_librarian.validators import validate_path


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
    assert "No generated overview." in markdown
    assert "No semantic summary" not in markdown
    quality = review_note_quality(markdown_path)
    assert quality.passed is True


def test_pdf_ocr_requires_include_pdf(tmp_path):
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()

    with pytest.raises(ValueError, match="PDF OCR requires --include-pdf"):
        ingest_inbox(inbox, tmp_path, mode="read-only", pdf_ocr=True)


def test_pdf_ocr_requires_docling_converter(tmp_path):
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()

    with pytest.raises(ValueError, match="PDF OCR requires --pdf-converter docling"):
        ingest_inbox(inbox, tmp_path, mode="read-only", include_pdf=True, pdf_ocr=True)


def test_scanned_pdf_docling_without_ocr_remains_deferred(tmp_path):
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "scan.pdf").write_bytes(scanned_pdf_bytes())

    def fail_if_called(path):
        raise AssertionError("converter should not run for OCR-deferred scanned PDF")

    ingest_inbox(
        inbox,
        tmp_path,
        mode="draft",
        include_pdf=True,
        pdf_converter="docling",
        pdf_converter_func=fail_if_called,
    )

    root = tmp_path / "90_Staging" / "pdf" / "scan"
    manifest_payload = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_payload["status"] == "skipped"
    assert manifest_payload["classification"] == "scanned_pdf"
    assert manifest_payload["extraction"]["ocr_enabled"] is False
    assert [warning["code"] for warning in manifest_payload["extraction"]["warnings"]] == [
        "ocr_needed"
    ]
    assert not (root / "source.md").exists()
    assert not (root / "docling.json").exists()


def test_scanned_pdf_docling_ocr_writes_review_required_outputs(tmp_path):
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "scan.pdf").write_bytes(scanned_pdf_bytes())

    def fake_ocr_converter(path):
        return DoclingConversionResult(
            markdown="OCR extracted text Sentinel-OCR",
            structured_json='{"pages": 1, "ocr": true}\n',
            engine_version="mock-docling-ocr",
        )

    result = ingest_inbox(
        inbox,
        tmp_path,
        mode="draft",
        include_pdf=True,
        pdf_converter="docling",
        pdf_ocr=True,
        pdf_ocr_converter_func=fake_ocr_converter,
    )

    root = tmp_path / "90_Staging" / "pdf" / "scan"
    manifest_payload = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    markdown = (root / "source.md").read_text(encoding="utf-8")

    assert (root / "docling.json").exists()
    assert result.pdf_manifests[0].status == "needs_review"
    assert manifest_payload["status"] == "needs_review"
    assert manifest_payload["extraction"]["method"] == "ocr"
    assert manifest_payload["extraction"]["ocr_enabled"] is True
    assert "ocr_review_required" in {
        warning["code"] for warning in manifest_payload["extraction"]["warnings"]
    }
    assert "OCR warning" in markdown
    assert "OCR extracted text Sentinel-OCR" in markdown
    assert "status: \"staged\"" in markdown
    assert "review_required: true" in markdown
    assert "confidence: \"ocr-derived-needs-review\"" in markdown
    assert "extraction_method: \"ocr\"" in markdown
    assert "ocr_enabled: true" in markdown
    assert validate_path(tmp_path / "90_Staging").passed is True


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


def test_cli_pdf_ocr_requires_include_pdf(tmp_path, capsys):
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()

    exit_code = cli_main(
        [
            "ingest",
            str(inbox),
            "--vault",
            str(tmp_path),
            "--mode",
            "draft",
            "--pdf-ocr",
        ]
    )

    assert exit_code == 2
    assert "PDF OCR requires --include-pdf" in capsys.readouterr().out


def test_cli_pdf_ocr_passes_flag_to_ingest(tmp_path, monkeypatch):
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    captured = {}

    def fake_ingest(inbox_root, vault_root, **kwargs):
        captured.update(kwargs)
        return IngestRunResult(
            inbox_root=inbox_root,
            vault_root=vault_root,
            mode=kwargs["mode"],
        )

    monkeypatch.setattr("obsidian_librarian.cli.ingest_inbox", fake_ingest)

    exit_code = cli_main(
        [
            "ingest",
            str(inbox),
            "--vault",
            str(tmp_path),
            "--mode",
            "draft",
            "--include-pdf",
            "--pdf-converter",
            "docling",
            "--pdf-ocr",
        ]
    )

    assert exit_code == 0
    assert captured["include_pdf"] is True
    assert captured["pdf_converter"] == "docling"
    assert captured["pdf_ocr"] is True
