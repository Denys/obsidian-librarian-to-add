from __future__ import annotations

import json
from pathlib import Path

import pytest

from obsidian_librarian.pdf_docling import DoclingAsset, DoclingConversionResult
from obsidian_patron.docling_pipe import ingest_pdf_to_ingestion, slugify
from obsidian_patron.safety import archive_existing_slug, ensure_under


def _fake_conversion() -> DoclingConversionResult:
    return DoclingConversionResult(
        markdown="# Converted\n\nBody",
        structured_json='{"kind":"docling"}',
        engine_version="docling-test",
        tables_json='[{"rows": 1}]',
        assets=(DoclingAsset(relative_path="img.png", content=b"png"),),
    )


def test_slugify_is_deterministic() -> None:
    assert slugify("Power Electronics 101") == "power-electronics-101"
    assert slugify("  ***  ") == "document"


def test_ensure_under_rejects_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    with pytest.raises(ValueError):
        ensure_under(root, tmp_path / "outside")


def test_archive_existing_slug_uses_suffix_when_collision(tmp_path: Path) -> None:
    ingestion_root = tmp_path / "91_Ingestion"
    ingestion_root.mkdir()

    current = ingestion_root / "book"
    current.mkdir()

    archive = ingestion_root / "_archive"
    archive.mkdir()
    (archive / "book").mkdir()

    archived = archive_existing_slug(ingestion_root=ingestion_root, slug_dir=current)
    assert archived == archive / "book-2"
    assert archived.exists()


def test_ingest_pdf_creates_expected_tree_and_manifest(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    pdf = tmp_path / "analog.pdf"
    pdf.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n")

    monkeypatch.setattr(
        "obsidian_patron.docling_pipe.convert_pdf_with_docling",
        lambda _p: _fake_conversion(),
    )

    result = ingest_pdf_to_ingestion(pdf, vault)
    out = result.output_dir

    assert (out / "index.md").exists()
    assert (out / "00_metadata.md").exists()
    assert (out / "01_full-document.md").exists()
    assert (out / "attachments" / "fig_0001_img.png").exists()
    assert (out / "tables").exists()
    assert result.manifest_path.exists()

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert payload["document_type"] == "pdf"
    assert payload["ingest_tool"] == "docling"
    assert payload["origin"] == "analog"
    assert payload["outputs"]["attachments_count"] == 1
    assert payload["outputs"]["tables_count"] == 1


def test_ingest_pdf_existing_slug_requires_force(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "obsidian_patron.docling_pipe.convert_pdf_with_docling",
        lambda _p: _fake_conversion(),
    )

    ingest_pdf_to_ingestion(pdf, vault)
    with pytest.raises(FileExistsError):
        ingest_pdf_to_ingestion(pdf, vault, force=False)


def test_ingest_manifest_and_frontmatter_include_ingest_run_id(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    pdf = tmp_path / "timing.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "obsidian_patron.docling_pipe.convert_pdf_with_docling",
        lambda _p: _fake_conversion(),
    )

    result = ingest_pdf_to_ingestion(pdf, vault)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    run_id = manifest["ingest_run_id"]
    assert run_id

    index_text = (result.output_dir / "index.md").read_text(encoding="utf-8")
    metadata_text = (result.output_dir / "00_metadata.md").read_text(encoding="utf-8")
    full_document_text = (result.output_dir / "01_full-document.md").read_text(encoding="utf-8")
    assert f"ingest_run_id: {run_id}" in index_text
    assert f"ingest_run_id: {run_id}" in metadata_text
    assert f"ingest_run_id: {run_id}" in full_document_text
    assert "status: ingested" in full_document_text
    assert "origin: timing" in full_document_text
    assert f"source_pdf: {pdf.resolve(strict=False).as_posix()}" in full_document_text
    assert "section: full-document" in full_document_text


def test_ingest_conversion_failure_leaves_no_slug_directory(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    pdf = tmp_path / "fails.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    def raise_error(_p: str | Path) -> DoclingConversionResult:
        raise RuntimeError("docling boom")

    monkeypatch.setattr(
        "obsidian_patron.docling_pipe.convert_pdf_with_docling",
        raise_error,
    )

    with pytest.raises(RuntimeError):
        ingest_pdf_to_ingestion(pdf, vault)

    assert not (vault / "91_Ingestion" / "fails").exists()


def test_force_failure_preserves_existing_slug_directory(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    pdf = tmp_path / "keep.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "obsidian_patron.docling_pipe.convert_pdf_with_docling",
        lambda _p: _fake_conversion(),
    )
    first = ingest_pdf_to_ingestion(pdf, vault)
    original_text = (first.output_dir / "01_full-document.md").read_text(encoding="utf-8")

    def raise_error(_p: str | Path) -> DoclingConversionResult:
        raise RuntimeError("docling boom")

    monkeypatch.setattr(
        "obsidian_patron.docling_pipe.convert_pdf_with_docling",
        raise_error,
    )

    with pytest.raises(RuntimeError):
        ingest_pdf_to_ingestion(pdf, vault, force=True)

    out_dir = vault / "91_Ingestion" / "keep"
    assert out_dir.exists()
    assert (out_dir / "01_full-document.md").read_text(encoding="utf-8") == original_text
    assert not (vault / "91_Ingestion" / "_archive" / "keep").exists()
