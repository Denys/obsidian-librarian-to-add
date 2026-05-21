from __future__ import annotations

from pathlib import Path

import pytest

from obsidian_librarian.indexer import build_index
from obsidian_librarian.search import search_index


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_search_is_deterministic(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "one.md", "# Daisy Reverb\n\n#tag")
    _write(tmp_path / "B" / "two.md", "# Daisy Reverb\n\n#tag")
    idx = build_index(tmp_path, "vault").indexed_records
    summary = search_index(idx, "daisy", "vault")
    assert [h.path for h in summary.hits] == sorted([h.path for h in summary.hits])


def test_search_invalid_query_fails(tmp_path: Path) -> None:
    _write(tmp_path / "a.md", "# x")
    idx = build_index(tmp_path, "vault").indexed_records
    with pytest.raises(ValueError):
        search_index(idx, "   ", "vault")
