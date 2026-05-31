from __future__ import annotations

from pathlib import Path

from obsidian_librarian.gui.service import (
    action_registry,
    browse_directory,
    build_action_argv,
    effective_tier,
    run_action,
    save_pasted_source,
)


def test_action_registry_serializes_full_surface() -> None:
    registry = action_registry()
    ids = {action["id"] for action in registry}

    assert "librarian_ingest" in ids
    assert "librarian_validate" in ids
    assert "librarian_review_quality" in ids
    assert "librarian_index" in ids
    assert "librarian_search" in ids
    assert "librarian_enrich" in ids
    assert "patron_ingest" in ids
    assert "patron_propose" in ids
    assert "patron_link" in ids
    assert "patron_unmatched" in ids
    assert "patron_status" in ids
    assert "patron_promote" in ids
    assert "patron_unpromote" in ids


def test_ingest_argv_builder_matches_cli_shape(tmp_path: Path) -> None:
    inbox = tmp_path / "00_Inbox"
    vault = tmp_path / "vault"
    argv = build_action_argv(
        "librarian_ingest",
        {
            "inbox": str(inbox),
            "vault": str(vault),
            "mode": "draft",
            "include_pdf": True,
            "pdf_converter": "docling",
            "pdf_ocr": True,
        },
    )

    assert argv == [
        "ingest",
        str(inbox),
        "--vault",
        str(vault),
        "--mode",
        "draft",
        "--include-pdf",
        "--pdf-converter",
        "docling",
        "--pdf-ocr",
    ]
    assert effective_tier("librarian_ingest", {"mode": "read-only"}) == "read-only"
    assert effective_tier("librarian_ingest", {"mode": "draft"}) == "staging-write"


def test_write_action_without_confirmation_does_not_execute(tmp_path: Path) -> None:
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "note.md").write_text("# Note\n", encoding="utf-8")

    result = run_action(
        "librarian_ingest",
        {"inbox": str(inbox), "vault": str(tmp_path), "mode": "draft"},
        confirmed=False,
    )

    assert result["status"] == "needs_confirmation"
    assert result["executed"] is False
    assert result["safety_tier"] == "staging-write"
    assert "obsidian-librarian" in result["equivalent_cli"]
    assert not (tmp_path / "90_Staging").exists()


def test_read_only_action_executes_and_captures_output(tmp_path: Path) -> None:
    note = tmp_path / "Notes" / "daisy.md"
    note.parent.mkdir()
    note.write_text("# Daisy\n", encoding="utf-8")

    result = run_action(
        "librarian_search",
        {"query": "daisy", "vault": str(tmp_path), "scope": "vault"},
        confirmed=False,
    )

    assert result["status"] == "ok"
    assert result["executed"] is True
    assert result["exit_code"] == 0
    assert "# Obsidian Librarian Search" in result["stdout"]
    assert "Notes/daisy.md" in result["stdout"]


def test_save_pasted_source_creates_temp_inbox_with_provenance() -> None:
    result = save_pasted_source("# Pasted\n", "md")

    file_path = Path(result["file_path"])
    inbox_dir = Path(result["inbox_dir"])

    assert file_path.exists()
    assert file_path.parent == inbox_dir
    assert file_path.suffix == ".md"
    assert file_path.read_text(encoding="utf-8") == "# Pasted\n"
    assert "pasted source" in result["provenance"]


def test_confirmed_draft_ingest_writes_only_staging(tmp_path: Path) -> None:
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    source = inbox / "note.md"
    source.write_text("# Note\n", encoding="utf-8")

    result = run_action(
        "librarian_ingest",
        {"inbox": str(inbox), "vault": str(tmp_path), "mode": "draft"},
        confirmed=True,
    )

    assert result["status"] == "ok"
    assert result["exit_code"] == 0
    assert (tmp_path / "90_Staging" / "Sources" / "note_md.source.md").exists()
    assert source.read_text(encoding="utf-8") == "# Note\n"


def test_browse_directory_lists_parent_and_entries(tmp_path: Path) -> None:
    (tmp_path / "folder").mkdir()
    (tmp_path / "note.md").write_text("# Note\n", encoding="utf-8")

    result = browse_directory(str(tmp_path))

    assert result["path"] == str(tmp_path.resolve(strict=False))
    assert result["parent"] == str(tmp_path.parent.resolve(strict=False))
    entries = {entry["name"]: entry["is_dir"] for entry in result["entries"]}
    assert entries["folder"] is True
    assert entries["note.md"] is False
