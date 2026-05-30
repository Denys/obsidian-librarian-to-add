from __future__ import annotations

from pathlib import Path

import pytest

from obsidian_librarian.cli import main


def test_cli_index_and_search(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    note = tmp_path / "Notes" / "a.md"
    note.parent.mkdir(parents=True)
    note.write_text("# Daisy", encoding="utf-8")

    idx_code = main(["index", "--vault", str(tmp_path), "--scope", "vault"])
    idx_out = capsys.readouterr().out
    assert idx_code == 0
    assert "Indexed records" in idx_out

    search_code = main(["search", "daisy", "--vault", str(tmp_path), "--scope", "vault"])
    search_out = capsys.readouterr().out
    assert search_code == 0
    assert "Matched files" in search_out

    ingestion = tmp_path / "91_Ingestion" / "book" / "chapter.md"
    ingestion.parent.mkdir(parents=True)
    ingestion.write_text("# Buck Converter", encoding="utf-8")

    ingestion_code = main(["search", "buck", "--vault", str(tmp_path), "--scope", "ingestion"])
    ingestion_out = capsys.readouterr().out
    assert ingestion_code == 0
    assert "91_Ingestion/book/chapter.md" in ingestion_out


def test_cli_invalid_scope_error() -> None:
    with pytest.raises(SystemExit):
        main(["index", "--scope", "bad"])
