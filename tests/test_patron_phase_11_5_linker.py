from __future__ import annotations

from pathlib import Path

from obsidian_patron.cli import main
from obsidian_patron.linker import link_ingested_notes


def test_link_ingested_notes_matches_existing_title_and_reports_unmatched(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    trusted = vault / "20_Power-Electronics"
    trusted.mkdir(parents=True)
    (trusted / "Buck Converter.md").write_text(
        "---\ntitle: Buck Converter\n---\n# Buck Converter\n", encoding="utf-8"
    )

    slug_dir = vault / "91_Ingestion" / "power-book"
    slug_dir.mkdir(parents=True)
    note = slug_dir / "01_chapter.md"
    note.write_text(
        "# Chapter One\n\nA **Buck Converter** regulates output. **Flux Capacitor** is unrelated.\n",
        encoding="utf-8",
    )

    result = link_ingested_notes("power-book", vault)

    assert result.matched_count == 1
    assert result.unmatched_count == 2
    assert "[[Buck Converter|Buck Converter]]" in note.read_text(encoding="utf-8")
    report = (slug_dir / "_unmatched_candidates.md").read_text(encoding="utf-8")
    assert report.startswith("# Candidate notes - review before creating manually")
    assert "Flux Capacitor" in report
    assert not (trusted / "Flux Capacitor.md").exists()


def test_link_ingested_notes_skips_fenced_code_blocks(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    trusted = vault / "20_Power-Electronics"
    trusted.mkdir(parents=True)
    (trusted / "Buck Converter.md").write_text(
        "---\ntitle: Buck Converter\n---\n# Buck Converter\n", encoding="utf-8"
    )

    slug_dir = vault / "91_Ingestion" / "power-book"
    slug_dir.mkdir(parents=True)
    note = slug_dir / "01_chapter.md"
    note.write_text(
        "# Chapter One\n\n"
        "```python\n"
        'print("Buck Converter")\n'
        "```\n\n"
        "**Buck Converter** appears in prose.\n",
        encoding="utf-8",
    )

    link_ingested_notes("power-book", vault)

    content = note.read_text(encoding="utf-8")
    assert 'print("Buck Converter")' in content
    assert "[[Buck Converter|Buck Converter]]" in content


def test_link_command_errors_for_missing_slug(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()

    assert main(["link", "missing", "--vault", str(vault)]) == 2
