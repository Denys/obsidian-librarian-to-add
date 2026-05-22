"""Deterministic Markdown/TXT ingest orchestration."""

from __future__ import annotations

from pathlib import Path

from obsidian_librarian.config import LibrarianConfig
from obsidian_librarian.models import GeneratedNote, IngestRunResult
from obsidian_librarian.parser import parse_inbox
from obsidian_librarian.pdf_classifier import (
    classify_pdf_source,
    discover_pdf_sources,
    render_pdf_manifest_json,
    staged_pdf_manifest_path,
)
from obsidian_librarian.renderers import render_source_note, staged_source_note_path
from obsidian_librarian.review_report import render_review_report
from obsidian_librarian.vault import ObsidianVault

VALID_INGEST_MODES = {"read-only", "draft"}


def ingest_inbox(
    inbox_root: str | Path,
    vault_root: str | Path,
    *,
    mode: str = "draft",
    include_pdf: bool = False,
) -> IngestRunResult:
    """Ingest supported inbox files into staged Obsidian notes.

    Markdown/TXT ingest remains deterministic. Phase 11.1 PDF support only discovers PDFs,
    classifies them, and optionally writes manifest JSON sidecars. It does not convert PDFs
    to Markdown, run OCR, call models, add embeddings, or modify source PDFs.
    """
    if mode not in VALID_INGEST_MODES:
        raise ValueError(f"Unsupported ingest mode: {mode}")

    inbox_path = Path(inbox_root).expanduser().resolve(strict=False)
    config = LibrarianConfig.from_paths(vault_root)
    vault = ObsidianVault(config)
    documents, skipped = parse_inbox(inbox_path, include_pdf=include_pdf)
    pdf_manifests = []

    if include_pdf:
        pdf_manifests = [
            classify_pdf_source(path, source_root=inbox_path) for path in discover_pdf_sources(inbox_path)
        ]

    result = IngestRunResult(
        inbox_root=inbox_path,
        vault_root=config.resolved_vault_root,
        mode=mode,
        processed=documents,
        skipped=skipped,
        pdf_manifests=pdf_manifests,
    )

    if include_pdf:
        result.warnings.append(
            "PDF intake is Phase 11.1 classifier/manifest only; no PDF Markdown conversion or OCR was run."
        )

    if mode == "read-only":
        result.warnings.append("Read-only mode: no staged notes or reports were written.")
        return result

    for document in documents:
        note_relative_path = staged_source_note_path(document)
        note_content = render_source_note(document)
        write_result = vault.write_staged_text_unique(note_relative_path, note_content)
        result.generated.append(
            GeneratedNote(
                source_path=document.path,
                staged_path=write_result.path,
                note_type="source",
            )
        )

    for manifest in pdf_manifests:
        manifest_relative_path = staged_pdf_manifest_path(manifest)
        manifest_content = render_pdf_manifest_json(manifest)
        write_result = vault.write_staged_text_unique(manifest_relative_path, manifest_content)
        result.pdf_manifest_paths.append(write_result.path)

    report_content = render_review_report(result)
    report_write = vault.write_staged_text_unique("review_report.md", report_content)
    result.report_path = report_write.path

    return result
