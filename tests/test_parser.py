"""Tests for deterministic inbox parsing."""

from __future__ import annotations

from pathlib import Path

from obsidian_librarian.parser import extract_action_items, extract_title, parse_inbox


def test_parse_inbox_reads_markdown_and_text_and_skips_other_files(tmp_path: Path) -> None:
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "note.md").write_text("# Markdown Note\n\nTODO: act\n", encoding="utf-8")
    (inbox / "plain.txt").write_text("Plain title\nBody", encoding="utf-8")
    (inbox / "image.png").write_text("not really an image", encoding="utf-8")

    documents, skipped = parse_inbox(inbox)

    assert [document.relative_path.as_posix() for document in documents] == ["note.md", "plain.txt"]
    assert [document.source_kind for document in documents] == ["markdown", "text"]
    assert documents[0].title == "Markdown Note"
    assert documents[0].action_items == ("TODO: act",)
    assert len(skipped) == 1
    assert skipped[0].path.name == "image.png"
    assert skipped[0].reason == "unsupported extension"


def test_parse_inbox_preserves_nested_relative_paths(tmp_path: Path) -> None:
    inbox = tmp_path / "00_Inbox"
    nested = inbox / "project" / "subtopic"
    nested.mkdir(parents=True)
    (nested / "note.md").write_text("# Nested\n", encoding="utf-8")

    documents, skipped = parse_inbox(inbox)

    assert skipped == []
    assert len(documents) == 1
    assert documents[0].relative_path.as_posix() == "project/subtopic/note.md"


def test_extract_title_uses_first_heading_or_first_non_empty_line(tmp_path: Path) -> None:
    assert extract_title("\n# Heading\nBody", tmp_path / "note.md") == "Heading"
    assert extract_title("\nPlain line\nBody", tmp_path / "note.md") == "Plain line"
    assert extract_title("\n\n", tmp_path / "fallback.md") == "fallback"


def test_extract_action_items_is_conservative() -> None:
    content = "\n".join(
        [
            "TODO: first",
            "- [ ] second",
            "* [ ] third",
            "Normal sentence with todo inside should not be extracted",
        ]
    )

    assert extract_action_items(content) == ("TODO: first", "- [ ] second", "* [ ] third")
