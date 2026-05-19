"""Tests for staged note renderers."""

from __future__ import annotations

from pathlib import Path

from obsidian_librarian.models import SourceDocument
from obsidian_librarian.renderers import render_source_note, staged_source_note_path


def make_source(relative_path: str = "note.md") -> SourceDocument:
    return SourceDocument(
        path=Path("/vault/00_Inbox") / relative_path,
        relative_path=Path(relative_path),
        source_kind="markdown",
        title="Example Note",
        content="# Example Note\n\nTODO: act\n",
        action_items=("TODO: act",),
    )


def test_staged_source_note_path_is_stable() -> None:
    source = make_source("project alpha/note one.md")

    assert staged_source_note_path(source).as_posix() == (
        "Sources/project-alpha/note-one_md.source.md"
    )


def test_render_source_note_preserves_source_reference_and_actions() -> None:
    source = make_source()

    rendered = render_source_note(source)

    assert "type: \"source\"" in rendered
    assert "source_path: \"note.md\"" in rendered
    assert "status: \"staged\"" in rendered
    assert "# Example Note" in rendered
    assert "TODO: act" in rendered
    assert "Source path: `note.md`" in rendered


def test_render_source_note_handles_empty_content() -> None:
    source = SourceDocument(
        path=Path("/vault/00_Inbox/empty.txt"),
        relative_path=Path("empty.txt"),
        source_kind="text",
        title="empty",
        content="",
    )

    rendered = render_source_note(source)

    assert "Source file is empty." in rendered
    assert "No action items extracted deterministically." in rendered
