"""Review report rendering for ingest runs."""

from __future__ import annotations

from pathlib import Path

from obsidian_librarian.models import GeneratedNote, IngestRunResult, SkippedFile, SourceDocument


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
        f"- `{document.relative_path.as_posix()}` ({document.source_kind}) — {document.title}"
        for document in documents
    ]


def render_skipped_files(skipped_files: list[SkippedFile]) -> list[str]:
    """Render skipped file rows."""
    if not skipped_files:
        return ["No files skipped."]

    return [f"- `{path_for_report(item.path)}` — {item.reason}" for item in skipped_files]


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
