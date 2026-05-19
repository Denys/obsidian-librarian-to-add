"""Tests for deterministic staged-note quality review."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from obsidian_librarian.note_quality import review_note_quality, review_note_quality_path


def write_note(path: Path, body: str) -> Path:
    """Write a staged-note fixture."""
    path.write_text(body, encoding="utf-8")
    return path


def source_note(
    *,
    source_path: str | None = "inbox/source.md",
    status: str | None = "staged",
    note_type: str | None = "source",
    summary: str = "No deterministic summary generated in Phase 3.",
    key_claims: str = "No key claims extracted deterministically in Phase 3.",
    action_items: str = "No action items extracted deterministically.",
    links: str = "- Source path: `inbox/source.md`",
) -> str:
    """Return a source-note fixture with optional missing frontmatter fields."""
    frontmatter = ["---"]
    if note_type is not None:
        frontmatter.append(f'type: "{note_type}"')
    frontmatter.append('source_kind: "markdown"')
    if source_path is not None:
        frontmatter.append(f'source_path: "{source_path}"')
    frontmatter.append('project: "unknown"')
    if status is not None:
        frontmatter.append(f'status: "{status}"')
    frontmatter.append('confidence: "source-backed"')
    frontmatter.append("---")

    return (
        "\n".join(frontmatter)
        + "\n\n"
        "# Source Note\n\n"
        "## Summary\n\n"
        f"{summary}\n\n"
        "## Key claims\n\n"
        f"{key_claims}\n\n"
        "## Action items\n\n"
        f"{action_items}\n\n"
        "## Open questions\n\n"
        "No open questions extracted deterministically in Phase 3.\n\n"
        "## Links\n\n"
        f"{links}\n"
    )


def finding_ids(result: Any) -> set[str]:
    """Return finding ids from a quality result or summary-like object."""
    return {finding.check_id for finding in result.blocking_findings}


def suggestion_ids(result: Any) -> set[str]:
    """Return suggestion ids from a quality result or summary-like object."""
    return {suggestion.check_id for suggestion in result.suggestions}


def test_review_note_quality_flags_missing_required_frontmatter(tmp_path: Path) -> None:
    note = write_note(
        tmp_path / "missing.md",
        source_note(source_path=None, status=None, note_type=None),
    )

    result = review_note_quality(note)

    assert finding_ids(result) == {
        "missing_type",
        "missing_source_path",
        "missing_staged_status",
    }
    assert not result.passed


def test_review_note_quality_blocks_action_items_collapsed_into_claims(tmp_path: Path) -> None:
    note = write_note(
        tmp_path / "collapsed.md",
        source_note(
            key_claims="- TODO: call Sam about the contract",
            action_items="No action items extracted deterministically.",
        ),
    )

    result = review_note_quality(note)

    assert "action_items_in_key_claims" in finding_ids(result)


def test_review_note_quality_blocks_overclaimed_placeholder_summary(tmp_path: Path) -> None:
    note = write_note(
        tmp_path / "overclaimed.md",
        source_note(summary="Semantic summary generated from deterministic placeholder."),
    )

    result = review_note_quality(note)

    assert "summary_overclaims_semantic_extraction" in finding_ids(result)


def test_review_note_quality_keeps_missing_wikilinks_as_suggestion(tmp_path: Path) -> None:
    note = write_note(tmp_path / "good.md", source_note())

    result = review_note_quality(note)

    assert result.passed
    assert "missing_wikilinks" in suggestion_ids(result)
    assert "missing_wikilinks" not in finding_ids(result)


def test_review_note_quality_path_summarizes_markdown_directory(tmp_path: Path) -> None:
    write_note(tmp_path / "good.md", source_note())
    write_note(tmp_path / "bad.md", source_note(source_path=None))
    write_note(tmp_path / "review_report.md", "# Report\n")

    summary = review_note_quality_path(tmp_path)

    assert len(summary.checked_files) == 2
    assert len(summary.skipped_files) == 1
    assert not summary.passed
    assert "missing_source_path" in finding_ids(summary)
