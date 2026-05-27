"""Review report rendering for ingest runs."""

from __future__ import annotations

from pathlib import Path

from obsidian_librarian.models import (
    GeneratedNote,
    IngestRunResult,
    PdfManifest,
    SkippedFile,
    SourceDocument,
)


def render_review_report(result: IngestRunResult) -> str:
    """Render a Markdown review report for an ingest run."""
    lines = [
        "# Obsidian Librarian Review Report",
        "",
        "## Run summary",
        "",
        f"- Mode: `{result.mode}`",
        f"- Vault root: `{result.vault_root}`",
        f"- Inbox root: `{result.inbox_root}`",
        f"- Processed files: {len(result.processed)}",
        f"- Skipped files: {len(result.skipped)}",
        f"- PDF manifests: {len(result.pdf_manifests)}",
        f"- Generated notes: {len(result.generated)}",
        "",
        "## Processed files",
        "",
        *render_processed_files(result.processed),
        "",
        "## Skipped files",
        "",
        *render_skipped_files(result.skipped),
        "",
        "## PDF manifests",
        "",
        *render_pdf_manifests(result.pdf_manifests, result.pdf_manifest_paths),
        "",
        "## Generated notes",
        "",
        *render_generated_notes(result.generated),
        "",
        "## Warnings",
        "",
        *render_warnings(result.warnings),
        "",
    ]
    return "\n".join(lines)


def render_processed_files(documents: list[SourceDocument]) -> list[str]:
    """Render processed file rows."""
    if not documents:
        return ["No files processed."]

    return [
        f"- `{document.relative_path.as_posix()}` ({document.source_kind}) - {document.title}"
        for document in documents
    ]


def render_skipped_files(skipped_files: list[SkippedFile]) -> list[str]:
    """Render skipped file rows."""
    if not skipped_files:
        return ["No files skipped."]

    return [f"- `{path_for_report(item.path)}` - {item.reason}" for item in skipped_files]


def render_pdf_manifests(manifests: list[PdfManifest], manifest_paths: list[Path]) -> list[str]:
    """Render PDF manifest rows."""
    if not manifests:
        return ["No PDF manifests generated."]

    rendered: list[str] = []
    for index, manifest in enumerate(manifests):
        manifest_path = manifest_paths[index] if index < len(manifest_paths) else None
        output = f" manifest: `{path_for_report(manifest_path)}`" if manifest_path else ""
        rendered.append(
            f"- `{manifest.source_path}` - {manifest.classification}, "
            f"status={manifest.status}, pages={manifest.page_count},{output}"
            f"{render_pdf_outputs_inline(manifest)}"
        )
        for warning in manifest.extraction.warnings:
            rendered.append(f"  - warning `{warning.code}`: {warning.message}")
    return rendered


def render_pdf_outputs_inline(manifest: PdfManifest) -> str:
    """Render generated PDF output references for review reports."""
    parts: list[str] = []
    if manifest.outputs.json_sidecar:
        parts.append(f"json=`{manifest.outputs.json_sidecar}`")
    if manifest.outputs.table_sidecars:
        tables = ", ".join(f"`{path}`" for path in manifest.outputs.table_sidecars)
        parts.append(f"tables={tables}")
    if manifest.outputs.asset_dir:
        parts.append(f"assets=`{manifest.outputs.asset_dir}`")
    if not parts:
        return ""
    return " outputs: " + ", ".join(parts)


def render_generated_notes(notes: list[GeneratedNote]) -> list[str]:
    """Render generated note rows."""
    if not notes:
        return ["No notes generated."]

    return [
        f"- `{path_for_report(note.staged_path)}` from `{path_for_report(note.source_path)}` "
        f"({note.note_type})"
        for note in notes
    ]


def render_warnings(warnings: list[str]) -> list[str]:
    """Render warning rows."""
    if not warnings:
        return ["No warnings."]

    return [f"- {warning}" for warning in warnings]


def path_for_report(path: Path) -> str:
    """Return a display-safe path string."""
    return path.as_posix()
