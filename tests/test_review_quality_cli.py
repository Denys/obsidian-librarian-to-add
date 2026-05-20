"""CLI tests for deterministic note-quality review."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.test_note_quality import source_note

from obsidian_librarian.cli import main


def test_cli_help_includes_review_quality(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "review-quality" in captured.out


def test_review_quality_valid_note_returns_zero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    note = tmp_path / "good.md"
    note.write_text(source_note(), encoding="utf-8")

    exit_code = main(["review-quality", str(note)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Verdict: pass with suggestions" in captured.out
    assert "Blocking findings: 0" in captured.out


def test_review_quality_missing_source_path_returns_one(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    note = tmp_path / "bad.md"
    note.write_text(source_note(source_path=None), encoding="utf-8")

    exit_code = main(["review-quality", str(note)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Verdict: fail" in captured.out
    assert "source_path" in captured.out.lower()


def test_review_quality_directory_checks_multiple_markdown_files(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "good.md").write_text(source_note(), encoding="utf-8")
    (tmp_path / "bad.md").write_text(source_note(source_path=None), encoding="utf-8")
    (tmp_path / "review_report.md").write_text("# Report", encoding="utf-8")

    exit_code = main(["review-quality", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Checked files: 2" in captured.out
    assert "Skipped files: 1" in captured.out


def test_review_quality_suggestions_do_not_fail_when_blocking_is_zero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    note = tmp_path / "good.md"
    note.write_text(source_note(), encoding="utf-8")

    exit_code = main(["review-quality", str(note)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Suggestions:" in captured.out
    assert "Verdict: pass with suggestions" in captured.out


def test_review_quality_invalid_path_returns_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["review-quality", str(tmp_path / "missing.md")])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Error:" in captured.out


def test_review_quality_non_markdown_file_returns_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    note = tmp_path / "note.txt"
    note.write_text("plain", encoding="utf-8")

    exit_code = main(["review-quality", str(note)])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "only supports markdown" in captured.out.lower()


def test_review_quality_directory_without_markdown_returns_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "note.txt").write_text("plain", encoding="utf-8")

    exit_code = main(["review-quality", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "no markdown notes" in captured.out.lower()
