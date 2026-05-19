"""Tests for staged note validation."""

from __future__ import annotations

from pathlib import Path

from obsidian_librarian.validators import (
    parse_frontmatter,
    render_validation_summary,
    validate_path,
)


VALID_SOURCE_NOTE = """---
type: \"source\"
source_kind: \"markdown\"
source_path: \"note.md\"
project: \"unknown\"
status: \"staged\"
confidence: \"source-backed\"
---

# Note

## Summary

Text.

## Key claims

Text.

## Action items

None.

## Open questions

None.

## Links

- Source path: `note.md`
"""


def test_parse_frontmatter_reads_simple_quoted_values() -> None:
    parsed = parse_frontmatter(VALID_SOURCE_NOTE)

    assert parsed["type"] == "source"
    assert parsed["source_path"] == "note.md"
    assert parsed["status"] == "staged"


def test_validate_path_passes_valid_source_note(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text(VALID_SOURCE_NOTE, encoding="utf-8")

    summary = validate_path(note)

    assert summary.passed is True
    assert summary.checked_files == [note.resolve(strict=False)]
    assert summary.issues == []


def test_validate_path_skips_review_reports(tmp_path: Path) -> None:
    report = tmp_path / "review_report.md"
    report.write_text("# Report\n", encoding="utf-8")

    summary = validate_path(tmp_path)

    assert summary.passed is True
    assert summary.checked_files == []
    assert summary.skipped_files == [report.resolve(strict=False)]


def test_validate_path_reports_missing_frontmatter(tmp_path: Path) -> None:
    note = tmp_path / "broken.md"
    note.write_text("# Broken\n", encoding="utf-8")

    summary = validate_path(note)

    assert summary.passed is False
    assert len(summary.issues) == 1
    assert "frontmatter" in summary.issues[0].message


def test_validate_path_reports_missing_required_section(tmp_path: Path) -> None:
    note = tmp_path / "broken.md"
    note.write_text(
        "---\n"
        "type: \"source\"\n"
        "source_kind: \"markdown\"\n"
        "source_path: \"note.md\"\n"
        "status: \"staged\"\n"
        "confidence: \"source-backed\"\n"
        "---\n\n"
        "# Broken\n",
        encoding="utf-8",
    )

    summary = validate_path(note)

    assert summary.passed is False
    assert any("Missing required section" in issue.message for issue in summary.issues)


def test_render_validation_summary_reports_failure(tmp_path: Path) -> None:
    note = tmp_path / "broken.md"
    note.write_text("# Broken\n", encoding="utf-8")
    summary = validate_path(note)

    rendered = render_validation_summary(summary)

    assert "Issues: 1" in rendered
    assert "Missing frontmatter" in rendered
