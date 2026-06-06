from __future__ import annotations

from pathlib import Path

import pytest

from olp_agent.folder_deployment import (
    classify_library_contents,
    deploy_library_folder,
    plan_ingest_wave,
    scan_library_folder,
)
from olp_agent.safety import ApprovalSet, assert_path_inside, require_approval
from olp_agent.tools import (
    run_librarian_ingest_draft,
    run_librarian_ingest_preview,
    run_librarian_search,
    run_patron_propose,
)


def test_deploy_library_folder_dry_run_does_not_create_files(tmp_path: Path) -> None:
    target = tmp_path / "library"
    target.mkdir()

    result = deploy_library_folder(
        target_root=str(target),
        profile="audiodsp",
        mode="dry_run",
        approvals=ApprovalSet(),
    )

    assert result.status == "ok"
    assert result.writes_performed is False
    assert str(target / "90_Staging") in result.planned_paths
    assert not (target / "90_Staging").exists()
    assert not (target / ".olp_agent").exists()


def test_deploy_library_folder_requires_approval_for_create(tmp_path: Path) -> None:
    target = tmp_path / "library"
    target.mkdir()

    result = deploy_library_folder(
        target_root=str(target),
        profile="audiodsp",
        mode="create_infrastructure",
        approvals=ApprovalSet(),
    )

    assert result.status == "needs_approval"
    assert "approve_create_infrastructure" in result.required_approvals
    assert not (target / "90_Staging").exists()


def test_deploy_library_folder_creates_only_infrastructure_when_approved(tmp_path: Path) -> None:
    target = tmp_path / "library"
    target.mkdir()
    source = target / "manual.pdf"
    source.write_text("raw pdf placeholder", encoding="utf-8")

    result = deploy_library_folder(
        target_root=str(target),
        profile="audiodsp",
        mode="create_infrastructure",
        approvals=ApprovalSet(approve_create_infrastructure=True),
    )

    assert result.status == "ok"
    assert result.writes_performed is True
    assert source.read_text(encoding="utf-8") == "raw pdf placeholder"
    assert (target / "00_Inbox").is_dir()
    assert (target / "10_DSP-Eurorack").is_dir()
    assert (target / "90_Staging").is_dir()
    assert (target / "91_Ingestion").is_dir()
    assert (target / ".olp_agent" / "deployment.json").is_file()


def test_scan_and_classify_library_contents(tmp_path: Path) -> None:
    target = tmp_path / "library"
    target.mkdir()
    (target / "paper.pdf").write_bytes(b"%PDF-1.4")
    (target / "notes.txt").write_text("oscillator notes", encoding="utf-8")
    (target / "table.xlsx").write_bytes(b"fake xlsx")

    inventory = scan_library_folder(str(target))
    classified = classify_library_contents(str(target), inventory)

    routes = {item.relative_path: item.route for item in classified.items}
    assert routes["paper.pdf"] == "patron"
    assert routes["notes.txt"] == "librarian"
    assert routes["table.xlsx"] == "manual_review"
    assert classified.summary["total_files"] == 3


def test_plan_ingest_wave_prefers_small_text_before_pdf(tmp_path: Path) -> None:
    target = tmp_path / "library"
    target.mkdir()
    (target / "book.pdf").write_bytes(b"x" * 2048)
    (target / "notes.txt").write_text("short notes", encoding="utf-8")

    inventory = scan_library_folder(str(target))
    classified = classify_library_contents(str(target), inventory)
    wave = plan_ingest_wave(str(target), classified, max_items=1)

    assert wave.status == "ok"
    assert len(wave.items) == 1
    assert wave.items[0].relative_path == "notes.txt"
    assert wave.items[0].route == "librarian"


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    with pytest.raises(ValueError):
        assert_path_inside(outside, [root])


def test_librarian_preview_uses_read_only_mode_and_explicit_vault(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    vault = tmp_path / "vault"
    vault.mkdir()

    result = run_librarian_ingest_preview(
        source_path=str(source),
        vault_root=str(vault),
        approvals=ApprovalSet(),
        execute=False,
    )

    assert result.status == "ok"
    argv = result.planned_commands[0].argv
    assert "--mode" in argv
    assert "read-only" in argv
    assert "--vault" in argv
    assert str(vault) in argv


def test_librarian_draft_requires_staging_write_approval(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    vault = tmp_path / "vault"
    vault.mkdir()

    result = run_librarian_ingest_draft(
        source_path=str(source),
        vault_root=str(vault),
        approvals=ApprovalSet(),
        execute=False,
    )

    assert result.status == "needs_approval"
    assert "approve_staging_write" in result.required_approvals


def test_patron_propose_requires_staging_write_even_without_llm(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()

    result = run_patron_propose(
        slug="test-slug",
        vault_root=str(vault),
        approvals=ApprovalSet(),
        llm=False,
        execute=False,
    )

    assert result.status == "needs_approval"
    assert "approve_staging_write" in result.required_approvals


def test_librarian_search_is_read_only_with_explicit_vault(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()

    result = run_librarian_search(
        vault_root=str(vault),
        query="oscillator",
        approvals=ApprovalSet(),
        execute=False,
    )

    assert result.status == "ok"
    argv = result.planned_commands[0].argv
    assert argv[2:] == [
        "obsidian_librarian.cli",
        "search",
        "oscillator",
        "--vault",
        str(vault),
        "--scope",
        "vault-and-staging",
    ]


def test_require_approval_reports_missing_flags() -> None:
    outcome = require_approval(
        ["approve_staging_write", "approve_llm"],
        ApprovalSet(approve_staging_write=True),
    )

    assert outcome.status == "needs_approval"
    assert outcome.required_approvals == ["approve_llm"]
