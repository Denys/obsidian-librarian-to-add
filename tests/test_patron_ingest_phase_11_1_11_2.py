from __future__ import annotations

import json
from pathlib import Path

import pytest

from obsidian_librarian.pdf_docling import DoclingAsset, DoclingConversionResult, DoclingSection
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


def _structured_conversion() -> DoclingConversionResult:
    return DoclingConversionResult(
        markdown="# Ignored fallback\n\nBody",
        structured_json='{"kind":"docling"}',
        engine_version="docling-test",
        tables_json='{"tables":[{"rows": 2}]}',
        assets=(
            DoclingAsset(
                relative_path="page-001-picture-001.png",
                content=b"captioned",
                caption="Figure 1: Converter Topology",
            ),
            DoclingAsset(relative_path="raw-image.bin", content=b"fallback"),
        ),
        sections=(
            DoclingSection(
                title="Chapter 1: Foundations",
                markdown="# Chapter 1: Foundations\n\nIntro text.",
            ),
            DoclingSection(
                title="Power Tables",
                markdown="# Power Tables\n\n| V | I |\n| - | - |",
            ),
            DoclingSection(
                title="Glossary",
                markdown="# Glossary\n\n- MOSFET: switch",
            ),
        ),
        metadata={
            "title": "Analog Handbook",
            "authors": ["Ada Lovelace", "Grace Hopper"],
            "year": 2026,
            "isbn": "978-1-2345-6789-0",
            "subject": "Power electronics",
            "keywords": ["analog", "converter"],
        },
        tables=({"path": "$.body.tables", "payload": [{"rows": 2}]},),
        code_blocks=("print('ok')",),
        figure_captions=("Figure 1: Converter Topology",),
        glossary_index_hints=("Glossary",),
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
    assert (out / "01_converted.md").exists()
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
    section_text = (result.output_dir / "01_converted.md").read_text(encoding="utf-8")
    assert f"ingest_run_id: {run_id}" in index_text
    assert f"ingest_run_id: {run_id}" in metadata_text
    assert f"ingest_run_id: {run_id}" in section_text
    assert "status: ingested" in section_text
    assert "origin: timing" in section_text
    assert f"source_pdf: {pdf.resolve(strict=False).as_posix()}" in section_text
    assert "section: converted" in section_text


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
    original_text = (first.output_dir / "01_converted.md").read_text(encoding="utf-8")

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
    assert (out_dir / "01_converted.md").read_text(encoding="utf-8") == original_text
    assert not (vault / "91_Ingestion" / "_archive" / "keep").exists()


def test_ingest_pdf_writes_multi_section_notes_and_toc_links(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    pdf = tmp_path / "analog handbook.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "obsidian_patron.docling_pipe.convert_pdf_with_docling",
        lambda _p: _structured_conversion(),
    )

    result = ingest_pdf_to_ingestion(pdf, vault)
    out = result.output_dir

    assert (out / "01_chapter-1-foundations.md").exists()
    assert (out / "02_power-tables.md").exists()
    assert (out / "03_glossary.md").exists()

    index_text = (out / "index.md").read_text(encoding="utf-8")
    assert "# analog handbook" in index_text
    assert "Ingest status: ingested" in index_text
    assert "[[01_chapter-1-foundations|Chapter 1: Foundations]]" in index_text
    assert "[[02_power-tables|Power Tables]]" in index_text
    assert "[[03_glossary|Glossary]]" in index_text

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["outputs"]["section_notes"] == [
        "01_chapter-1-foundations.md",
        "02_power-tables.md",
        "03_glossary.md",
    ]


def test_ingest_pdf_uses_caption_based_asset_names(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    pdf = tmp_path / "figures.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "obsidian_patron.docling_pipe.convert_pdf_with_docling",
        lambda _p: _structured_conversion(),
    )

    result = ingest_pdf_to_ingestion(pdf, vault)

    assert (result.output_dir / "attachments" / "fig_0001_figure-1-converter-topology.png").exists()
    assert (result.output_dir / "attachments" / "fig_0002_raw-image.png").exists()


def test_ingest_pdf_marks_glossary_index_section_note(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    pdf = tmp_path / "glossary.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "obsidian_patron.docling_pipe.convert_pdf_with_docling",
        lambda _p: _structured_conversion(),
    )

    result = ingest_pdf_to_ingestion(pdf, vault)
    glossary_text = (result.output_dir / "03_glossary.md").read_text(encoding="utf-8")
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert "section_kind: glossary-index" in glossary_text
    assert "- MOSFET: switch" in glossary_text
    assert manifest["outputs"]["glossary_index_hints"] == ["Glossary"]


def test_ingest_pdf_propagates_docling_metadata(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    pdf = tmp_path / "metadata.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "obsidian_patron.docling_pipe.convert_pdf_with_docling",
        lambda _p: _structured_conversion(),
    )

    result = ingest_pdf_to_ingestion(pdf, vault)
    metadata_text = (result.output_dir / "00_metadata.md").read_text(encoding="utf-8")
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert 'title: "Analog Handbook"' in metadata_text
    assert 'authors: ["Ada Lovelace", "Grace Hopper"]' in metadata_text
    assert "year: 2026" in metadata_text
    assert "isbn: 978-1-2345-6789-0" in metadata_text
    assert 'subject: "Power electronics"' in metadata_text
    assert 'keywords: [analog, converter]' in metadata_text
    assert f"ingest_run_id: {manifest['ingest_run_id']}" in metadata_text
    assert manifest["outputs"]["tables_count"] == 1
    assert manifest["outputs"]["code_blocks_count"] == 1
    assert manifest["outputs"]["figure_captions_count"] == 1
