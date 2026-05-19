"""Deterministic Markdown/TXT ingest orchestration."""

from __future__ import annotations

from pathlib import Path

from obsidian_librarian.config import LibrarianConfig
from obsidian_librarian.models import GeneratedNote, IngestRunResult
from obsidian_librarian.parser import parse_inbox
from obsidian_librarian.renderers import render_source_note, staged_source_note_path
from obsidian_librarian.review_report import render_review_report
from obsidian_librarian.vault import ObsidianVault

VALID_INGEST_MODES = {"read-only", "draft"}


def ingest_inbox(
    inbox_root: str | Path,
    vault_root: str | Path,
    *,
    mode: str = "draft",
) -> IngestRunResult:
    """Ingest supported inbox files into staged Obsidian notes.

    Phase 3 remains deterministic: it reads Markdown/TXT files, renders staged source notes,
    and emits a review report. It does not call models or external services.
    """
    if mode not in VALID_INGEST_MODES:
        raise ValueError(f"Unsupported ingest mode: {mode}")

    inbox_path = Path(inbox_root).expanduser().resolve(strict=False)
    config = LibrarianConfig.from_paths(vault_root)
    vault = ObsidianVault(config)
    documents, skipped = parse_inbox(inbox_path)

    result = IngestRunResult(
        inbox_root=inbox_path,
        vault_root=config.resolved_vault_root,
        mode=mode,
        processed=documents,
        skipped=skipped,
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

    report_content = render_review_report(result)
    report_write = vault.write_staged_text_unique("review_report.md", report_content)
    result.report_path = report_write.path

    return result
