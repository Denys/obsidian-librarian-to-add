from __future__ import annotations

from pathlib import Path

import pytest
from tests.test_note_quality import source_note

from obsidian_librarian.cli import main


def test_enrich_mock_single_file_draft(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    note = tmp_path / "90_Staging" / "Sources" / "a.md"
    note.parent.mkdir(parents=True)
    note.write_text(source_note(), encoding="utf-8")

    code = main(
        ["enrich", str(tmp_path / "90_Staging"), "--vault", str(tmp_path), "--mode", "draft"]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "Outputs: 1" in out
    assert (tmp_path / "90_Staging" / "Enriched").exists()


def test_enrich_invalid_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["enrich", str(tmp_path / "missing")])
    assert code == 2


def test_enrich_does_not_overwrite(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    note = tmp_path / "90_Staging" / "Sources" / "a.md"
    note.parent.mkdir(parents=True)
    note.write_text(source_note(), encoding="utf-8")
    code1 = main(
        ["enrich", str(tmp_path / "90_Staging"), "--vault", str(tmp_path), "--mode", "draft"]
    )
    capsys.readouterr()
    code2 = main(
        ["enrich", str(tmp_path / "90_Staging"), "--vault", str(tmp_path), "--mode", "draft"]
    )
    capsys.readouterr()
    assert code1 == 0 and code2 == 0
    enriched = list((tmp_path / "90_Staging" / "Enriched").glob("a.enriched*.md"))
    assert len(enriched) == 2



def test_enrich_refuses_path_outside_staging(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    note = tmp_path / "outside.md"
    note.write_text("# outside", encoding="utf-8")
    code = main(["enrich", str(note), "--vault", str(tmp_path), "--mode", "draft"])
    out = capsys.readouterr().out
    assert code == 2
    assert "within staging root" in out
