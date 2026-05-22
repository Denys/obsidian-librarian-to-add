"""Deterministic Markdown/TXT ingest orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from obsidian_librarian.config import LibrarianConfig
from obsidian_librarian.models import (
    GeneratedNote,
    IngestRunResult,
    PdfExtraction,
    PdfManifest,
    PdfOutputs,
    PdfWarning,
)
from obsidian_librarian.parser import parse_inbox
from obsidian_librarian.pdf_classifier import (
    classify_pdf_source,
    discover_pdf_sources,
    render_pdf_manifest_json,
    staged_pdf_manifest_path,
    staged_pdf_markdown_path,
    staged_pdf_structured_json_path,
)
from obsidian_librarian.pdf_docling import (
    DoclingConversionResult,
    PdfConversionError,
    PdfDependencyError,
    convert_pdf_with_docling,
)
from obsidian_librarian.renderers import render_source_note, staged_source_note_path, yaml_string
from obsidian_librarian.review_report import render_review_report
from obsidian_librarian.vault import ObsidianVault

VALID_INGEST_MODES = {"read-only", "draft"}
VALID_PDF_CONVERTERS = {"none", "docling"}
PdfConverterFunc = Callable[[str | Path], DoclingConversionResult]


def ingest_inbox(
    inbox_root: str | Path,
    vault_root: str | Path,
    *,
    mode: str = "draft",
    include_pdf: bool = False,
    pdf_converter: str = "none",
    pdf_converter_func: PdfConverterFunc | None = None,
) -> IngestRunResult:
    """Ingest supported inbox files into staged Obsidian notes.

    Markdown/TXT ingest remains deterministic. PDF conversion is explicit and optional.
    """
    if mode not in VALID_INGEST_MODES:
        raise ValueError(f"Unsupported ingest mode: {mode}")
    if pdf_converter not in VALID_PDF_CONVERTERS:
        raise ValueError(f"Unsupported PDF converter: {pdf_converter}")
    if pdf_converter != "none" and not include_pdf:
        raise ValueError("PDF conversion requires --include-pdf")

    inbox_path = Path(inbox_root).expanduser().resolve(strict=False)
    config = LibrarianConfig.from_paths(vault_root)
    vault = ObsidianVault(config)
    documents, skipped = parse_inbox(inbox_path, include_pdf=include_pdf)
    pdf_manifests = []

    if include_pdf:
        pdf_manifests = [
            classify_pdf_source(path, source_root=inbox_path)
            for path in discover_pdf_sources(inbox_path)
        ]

    result = IngestRunResult(
        inbox_root=inbox_path,
        vault_root=config.resolved_vault_root,
        mode=mode,
        processed=documents,
        skipped=skipped,
        pdf_manifests=pdf_manifests,
    )

    if include_pdf and pdf_converter == "none":
        result.warnings.append(
            "PDF intake is classifier/manifest only; no PDF Markdown conversion or OCR was run."
        )
    if include_pdf and pdf_converter == "docling":
        result.warnings.append("PDF conversion uses Docling; OCR remains disabled and deferred.")

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

    if pdf_converter == "docling":
        converter = pdf_converter_func or convert_pdf_with_docling
        pdf_manifests = convert_pdf_manifests(
            pdf_manifests,
            inbox_path,
            vault,
            converter,
            result,
        )
        result.pdf_manifests = pdf_manifests

    for manifest in pdf_manifests:
        manifest_relative_path = staged_pdf_manifest_path(manifest)
        manifest_content = render_pdf_manifest_json(manifest)
        write_result = vault.write_staged_text_unique(manifest_relative_path, manifest_content)
        result.pdf_manifest_paths.append(write_result.path)

    report_content = render_review_report(result)
    report_write = vault.write_staged_text_unique("review_report.md", report_content)
    result.report_path = report_write.path

    return result


def convert_pdf_manifests(
    manifests: list[PdfManifest],
    inbox_path: Path,
    vault: ObsidianVault,
    converter: PdfConverterFunc,
    result: IngestRunResult,
) -> list[PdfManifest]:
    """Convert eligible PDF manifests with Docling and write staged artifacts."""
    converted: list[PdfManifest] = []
    for manifest in manifests:
        if manifest.status not in {"staged", "needs_review"}:
            converted.append(manifest)
            continue

        source_pdf = inbox_path / manifest.source_path
        markdown_relative = staged_pdf_markdown_path(manifest)
        json_relative = staged_pdf_structured_json_path(manifest)

        try:
            conversion = converter(source_pdf)
        except PdfDependencyError as exc:
            raise ValueError(str(exc)) from exc
        except PdfConversionError as exc:
            converted.append(mark_pdf_conversion_failed(manifest, str(exc)))
            continue

        markdown_content = render_pdf_docling_note(manifest, conversion.markdown)
        markdown_write = vault.write_staged_text_unique(markdown_relative, markdown_content)
        json_write = vault.write_staged_text_unique(json_relative, conversion.structured_json)
        result.generated.append(
            GeneratedNote(
                source_path=source_pdf,
                staged_path=markdown_write.path,
                note_type="pdf_source",
            )
        )

        converted.append(
            mark_pdf_docling_converted(
                manifest,
                conversion,
                markdown_write.path.relative_to(vault.staging_root),
                json_write.path.relative_to(vault.staging_root),
            )
        )

    return converted


def mark_pdf_docling_converted(
    manifest: PdfManifest,
    conversion: DoclingConversionResult,
    markdown_relative: Path,
    json_relative: Path,
) -> PdfManifest:
    """Return a manifest updated with Docling output paths."""
    return replace(
        manifest,
        extraction=PdfExtraction(
            method="docling",
            engine_version=conversion.engine_version,
            ocr_enabled=False,
            warnings=manifest.extraction.warnings,
        ),
        outputs=PdfOutputs(
            markdown_note=markdown_relative.as_posix(),
            json_sidecar=json_relative.as_posix(),
        ),
    )


def mark_pdf_conversion_failed(manifest: PdfManifest, message: str) -> PdfManifest:
    """Return a manifest updated with a safe conversion failure."""
    warnings = (*manifest.extraction.warnings, PdfWarning("docling_failed", message))
    return replace(
        manifest,
        status="failed",
        extraction=PdfExtraction(
            method="docling",
            engine_version=None,
            ocr_enabled=False,
            warnings=warnings,
        ),
    )


def render_pdf_docling_note(manifest: PdfManifest, markdown: str) -> str:
    """Wrap Docling Markdown in a staged Obsidian source note."""
    return (
        "---\n"
        "type: \"source\"\n"
        "source_kind: \"pdf\"\n"
        f"source_path: {yaml_string(manifest.source_path)}\n"
        f"source_hash: {yaml_string(manifest.source_hash)}\n"
        f"page_count: {manifest.page_count}\n"
        "project: \"unknown\"\n"
        "status: \"staged\"\n"
        "confidence: \"source-backed\"\n"
        "extraction_method: \"docling\"\n"
        "ocr_enabled: false\n"
        "---\n\n"
        f"# {Path(manifest.source_path).stem}\n\n"
        "## Summary\n\n"
        "No semantic summary generated. This is staged Docling extraction output.\n\n"
        "## Key claims\n\n"
        "No key claims extracted deterministically in Phase 11.2.\n\n"
        "## Action items\n\n"
        "No action items extracted deterministically in Phase 11.2.\n\n"
        "## Open questions\n\n"
        "Review extraction quality, page ordering, tables, figures, and units before promotion.\n\n"
        "## Extracted content\n\n"
        f"{markdown.strip()}\n\n"
        "## Links\n\n"
        f"- Source path: `{manifest.source_path}`\n"
        f"- Source hash: `{manifest.source_hash}`\n"
    )
