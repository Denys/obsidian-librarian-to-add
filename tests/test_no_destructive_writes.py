"""Regression tests proving staged writes do not touch raw source files."""

from __future__ import annotations

from pathlib import Path

import pytest

from obsidian_librarian.config import LibrarianConfig
from obsidian_librarian.vault import ObsidianVault, VaultSafetyError


def test_raw_source_file_is_not_modified_by_staged_write(tmp_path: Path) -> None:
    source_dir = tmp_path / "00_Inbox"
    source_dir.mkdir()
    source_file = source_dir / "source.md"
    source_file.write_text("# Raw Source\nOriginal content\n", encoding="utf-8")

    vault = ObsidianVault(LibrarianConfig.from_paths(tmp_path))
    vault.write_staged_text("source.md", "# Generated Source Note\n")

    assert source_file.read_text(encoding="utf-8") == "# Raw Source\nOriginal content\n"
    assert (tmp_path / "90_Staging" / "source.md").read_text(encoding="utf-8") == (
        "# Generated Source Note\n"
    )


def test_attempt_to_target_inbox_through_staged_writer_is_refused(tmp_path: Path) -> None:
    source_dir = tmp_path / "00_Inbox"
    source_dir.mkdir()
    source_file = source_dir / "source.md"
    source_file.write_text("original", encoding="utf-8")

    vault = ObsidianVault(LibrarianConfig.from_paths(tmp_path))

    with pytest.raises(VaultSafetyError):
        vault.write_staged_text("../00_Inbox/source.md", "modified")

    assert source_file.read_text(encoding="utf-8") == "original"
