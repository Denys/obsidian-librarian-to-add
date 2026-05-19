"""Tests for safe staged vault writes."""

from __future__ import annotations

from pathlib import Path

import pytest

from obsidian_librarian.config import LibrarianConfig
from obsidian_librarian.vault import ObsidianVault, VaultSafetyError


def make_vault(tmp_path: Path) -> ObsidianVault:
    return ObsidianVault(LibrarianConfig.from_paths(tmp_path))


def test_write_staged_text_creates_file_under_staging(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)

    result = vault.write_staged_text("notes/example.md", "# Example\n")

    expected = tmp_path / "90_Staging" / "notes" / "example.md"
    assert result.path == expected.resolve(strict=False)
    assert result.created is True
    assert result.overwritten is False
    assert expected.read_text(encoding="utf-8") == "# Example\n"


def test_write_staged_text_refuses_overwrite_by_default(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    vault.write_staged_text("example.md", "first")

    with pytest.raises(FileExistsError):
        vault.write_staged_text("example.md", "second")

    assert (tmp_path / "90_Staging" / "example.md").read_text(encoding="utf-8") == "first"


def test_write_staged_text_can_overwrite_when_explicit(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    vault.write_staged_text("example.md", "first")

    result = vault.write_staged_text("example.md", "second", overwrite=True)

    assert result.created is False
    assert result.overwritten is True
    assert (tmp_path / "90_Staging" / "example.md").read_text(encoding="utf-8") == "second"


def test_absolute_staged_path_is_refused(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)

    with pytest.raises(VaultSafetyError):
        vault.write_staged_text(tmp_path / "outside.md", "bad")


def test_parent_traversal_is_refused(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)

    with pytest.raises(VaultSafetyError):
        vault.write_staged_text("../outside.md", "bad")

    assert not (tmp_path / "outside.md").exists()


def test_empty_staged_path_is_refused(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)

    with pytest.raises(VaultSafetyError):
        vault.write_staged_text(".", "bad")
