from __future__ import annotations

from pathlib import Path

from obsidian_librarian.indexer import build_index


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_index_scope_separation(tmp_path: Path) -> None:
    _write(tmp_path / "Notes" / "a.md", "# Vault\n\nTag #pv")
    _write(tmp_path / "90_Staging" / "Sources" / "b.md", "# Stage\n\n[[Link]]")
    _write(
        tmp_path / "91_Ingestion" / "book" / "c.md",
        "---\nstatus: ingested\nsource_pdf: book.pdf\nsource_section: Chapter 1\n"
        "ingest_run_id: run-1\naliases: [Power Alias]\n---\n# Ingested\n",
    )

    vault = build_index(tmp_path, "vault")
    staging = build_index(tmp_path, "staging")
    ingestion = build_index(tmp_path, "ingestion")
    both = build_index(tmp_path, "vault-and-staging")
    all_scopes = build_index(tmp_path, "all")

    assert all(r.scope == "vault" for r in vault.indexed_records)
    assert all(r.scope == "staging" for r in staging.indexed_records)
    assert all(r.scope == "ingestion" for r in ingestion.indexed_records)
    assert len(both.indexed_records) == 2
    assert len(all_scopes.indexed_records) == 3
    assert ingestion.indexed_records[0].source_pdf == "book.pdf"
    assert ingestion.indexed_records[0].source_section == "Chapter 1"
    assert ingestion.indexed_records[0].ingest_run_id == "run-1"
    assert ingestion.indexed_records[0].aliases == ["Power Alias"]


def test_index_extracts_fields(tmp_path: Path) -> None:
    _write(
        tmp_path / "Notes" / "a.md",
        "---\n"
        "status: trusted\n"
        "source_path: src.md\n"
        "---\n"
        "# Title\n\n"
        "## H1\n"
        "Tag #abc [[Wiki]] `src.md`",
    )
    summary = build_index(tmp_path, "vault")
    rec = summary.indexed_records[0]
    assert rec.title == "Title"
    assert "H1" in rec.headings
    assert "abc" in rec.tags
    assert "Wiki" in rec.wikilinks
    assert "src.md" in rec.source_refs


def test_set_frontmatter_fields_replaces_adds_and_removes() -> None:
    from obsidian_inventory import set_frontmatter_fields, split_frontmatter

    original = "---\nstatus: ingested\norigin: book\n---\n# Body\n\nText\n"
    updated = set_frontmatter_fields(
        original, {"status": "trusted", "promoted_at": "2026-05-30T00:00:00+00:00"}
    )

    # untouched field preserved, target replaced, new field appended, body intact
    assert "origin: book" in updated
    assert "status: trusted" in updated
    assert "status: ingested" not in updated
    assert "promoted_at: 2026-05-30T00:00:00+00:00" in updated
    assert split_frontmatter(updated)[1] == "# Body\n\nText\n"

    # None removes a key; removing the last field drops the frontmatter block entirely
    removed = set_frontmatter_fields("---\nstatus: trusted\n---\n# B\n", {"status": None})
    assert removed == "# B\n"


def test_split_frontmatter_handles_missing_block() -> None:
    from obsidian_inventory import split_frontmatter

    assert split_frontmatter("# No frontmatter\n") == ("", "# No frontmatter\n")
    assert split_frontmatter("---\nkey: val\n---\nbody\n") == ("key: val", "body\n")
