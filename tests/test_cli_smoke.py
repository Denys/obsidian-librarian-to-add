"""Smoke tests for the CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from obsidian_librarian.cli import main


def test_main_without_args_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "obsidian-librarian" in captured.out
    assert "ingest" in captured.out
    assert "validate" in captured.out
    assert "report" in captured.out


def test_ingest_command_creates_staged_note_and_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    source = inbox / "note.md"
    source.write_text("# Test Note\n\nTODO: verify ingest\n", encoding="utf-8")

    exit_code = main(["ingest", str(inbox), "--vault", str(tmp_path), "--mode", "draft"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Processed files: 1" in captured.out
    assert "Generated notes: 1" in captured.out
    assert (tmp_path / "90_Staging" / "Sources" / "note_md.source.md").exists()
    assert (tmp_path / "90_Staging" / "review_report.md").exists()
    assert source.read_text(encoding="utf-8") == "# Test Note\n\nTODO: verify ingest\n"


def test_ingest_read_only_writes_nothing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "note.txt").write_text("Plain text note", encoding="utf-8")

    exit_code = main(["ingest", str(inbox), "--vault", str(tmp_path), "--mode", "read-only"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Read-only mode" in captured.out
    assert not (tmp_path / "90_Staging").exists()


def test_validate_command_passes_valid_staged_note(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "note.md").write_text("# Test Note\n", encoding="utf-8")
    main(["ingest", str(inbox), "--vault", str(tmp_path), "--mode", "draft"])
    capsys.readouterr()

    exit_code = main(["validate", str(tmp_path / "90_Staging")])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Validation passed" in captured.out
    assert "Checked Markdown files" in captured.out


def test_report_command_is_registered_but_safe(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["report", "90_Staging"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "report" in captured.out
    assert "not implemented yet" in captured.out
