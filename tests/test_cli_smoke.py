"""Smoke tests for the Phase 1 CLI skeleton."""

from __future__ import annotations

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


def test_ingest_command_is_registered_but_safe(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["ingest", "00_Inbox", "--vault", ".", "--mode", "draft"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "ingest" in captured.out
    assert "not implemented in Phase 1" in captured.out


def test_validate_command_is_registered_but_safe(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["validate", "90_Staging"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "validate" in captured.out
    assert "not implemented in Phase 1" in captured.out


def test_report_command_is_registered_but_safe(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["report", "90_Staging"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "report" in captured.out
    assert "not implemented in Phase 1" in captured.out
