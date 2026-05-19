"""Integration tests for deterministic inbox ingest."""

from __future__ import annotations

from pathlib import Path

from obsidian_librarian.ingest import ingest_inbox


def test_ingest_inbox_writes_source_notes_and_review_report(tmp_path: Path) -> None:
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "alpha.md").write_text("# Alpha\n\nTODO: review alpha\n", encoding="utf-8")
    (inbox / "skip.pdf").write_text("unsupported", encoding="utf-8")

    result = ingest_inbox(inbox, tmp_path, mode="draft")

    source_note = tmp_path / "90_Staging" / "Sources" / "alpha_md.source.md"
    report = tmp_path / "90_Staging" / "review_report.md"

    assert len(result.processed) == 1
    assert len(result.skipped) == 1
    assert len(result.generated) == 1
    assert result.report_path == report
    assert source_note.exists()
    assert report.exists()

    source_note_text = source_note.read_text(encoding="utf-8")
    assert "source_path: \"alpha.md\"" in source_note_text
    assert "TODO: review alpha" in source_note_text

    report_text = report.read_text(encoding="utf-8")
    assert "Processed files: 1" in report_text
    assert "Skipped files: 1" in report_text
    assert "unsupported extension" in report_text


def test_ingest_inbox_read_only_does_not_create_staging(tmp_path: Path) -> None:
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "alpha.txt").write_text("Alpha", encoding="utf-8")

    result = ingest_inbox(inbox, tmp_path, mode="read-only")

    assert len(result.processed) == 1
    assert result.generated == []
    assert result.report_path is None
    assert not (tmp_path / "90_Staging").exists()


def test_ingest_inbox_uses_unique_paths_without_overwriting(tmp_path: Path) -> None:
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "alpha.md").write_text("# Alpha\n", encoding="utf-8")

    first = ingest_inbox(inbox, tmp_path, mode="draft")
    second = ingest_inbox(inbox, tmp_path, mode="draft")

    assert first.generated[0].staged_path.name == "alpha_md.source.md"
    assert second.generated[0].staged_path.name == "alpha_md.source_1.md"
    assert (tmp_path / "90_Staging" / "review_report.md").exists()
    assert (tmp_path / "90_Staging" / "review_report_1.md").exists()
