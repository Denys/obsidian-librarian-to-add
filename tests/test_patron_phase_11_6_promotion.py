from __future__ import annotations

import json
from pathlib import Path

import pytest

from obsidian_patron.cli import main
from obsidian_patron.promotion import promote_to_staging, promote_to_trusted, unpromote


def _write_slug(root: Path, slug: str = "book", *, selected_hub: str | None = None) -> Path:
    slug_dir = root / slug
    slug_dir.mkdir(parents=True)
    (slug_dir / "index.md").write_text(
        "---\nstatus: ingested\n---\n\n# Book\nBody\n",
        encoding="utf-8",
    )
    (slug_dir / "01_chapter.md").write_text(
        "---\nstatus: staged\n---\n\n# Chapter\nBody\n",
        encoding="utf-8",
    )
    (slug_dir / "_unmatched_candidates.md").write_text(
        "# Candidate notes — review before creating manually\n",
        encoding="utf-8",
    )
    if selected_hub is not None:
        (slug_dir / "_proposal.md").write_text(
            "# Proposal\n\n## Deterministic classification\n"
            f"- selected_hub: {selected_hub}\n",
            encoding="utf-8",
        )
    return slug_dir


def test_promote_to_staging_moves_from_ingestion_without_rewriting(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    source = _write_slug(vault / "91_Ingestion")
    original = (source / "index.md").read_text(encoding="utf-8")

    result = promote_to_staging("book", vault)

    destination = vault / "90_Staging" / "book"
    assert not source.exists()
    assert result.destination == destination.resolve(strict=False)
    assert (destination / "index.md").read_text(encoding="utf-8") == original
    ledger = json.loads((destination / "_promotion.json").read_text(encoding="utf-8"))
    assert ledger["promoted_to"] == "staging"


def test_promote_to_staging_fails_when_destination_exists(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_slug(vault / "91_Ingestion")
    _write_slug(vault / "90_Staging")

    with pytest.raises(FileExistsError):
        promote_to_staging("book", vault)


def test_promote_to_trusted_updates_note_frontmatter_and_skips_reports(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    source = _write_slug(vault / "90_Staging", selected_hub="20_Power-Electronics")
    hub = vault / "20_Power-Electronics"
    hub.mkdir(parents=True)
    report_before = (source / "_unmatched_candidates.md").read_text(encoding="utf-8")

    result = promote_to_trusted("book", vault, hub="20_Power-Electronics")

    destination = hub / "book"
    assert not source.exists()
    assert result.destination == destination.resolve(strict=False)
    assert "status: trusted" in (destination / "index.md").read_text(encoding="utf-8")
    assert "trusted_hub: 20_Power-Electronics" in (destination / "01_chapter.md").read_text(
        encoding="utf-8"
    )
    assert (destination / "_unmatched_candidates.md").read_text(encoding="utf-8") == report_before


def test_trusted_promotion_requires_matching_proposal_or_override(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_slug(vault / "90_Staging", selected_hub="10_DSP-Eurorack")
    (vault / "20_Power-Electronics").mkdir(parents=True)

    with pytest.raises(ValueError):
        promote_to_trusted("book", vault, hub="20_Power-Electronics")

    result = promote_to_trusted("book", vault, hub="20_Power-Electronics", override=True)
    assert result.destination == (vault / "20_Power-Electronics" / "book").resolve(strict=False)


def test_trusted_promotion_missing_proposal_requires_override(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_slug(vault / "91_Ingestion")
    (vault / "20_Power-Electronics").mkdir(parents=True)

    with pytest.raises(ValueError):
        promote_to_trusted("book", vault, hub="20_Power-Electronics")

    result = promote_to_trusted("book", vault, hub="20_Power-Electronics", override=True)
    assert result.promoted_to == "trusted"


def test_trusted_promotion_rejects_outside_or_missing_hub(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_slug(vault / "90_Staging", selected_hub="../outside")

    with pytest.raises(ValueError):
        promote_to_trusted("book", vault, hub="../outside", override=True)

    with pytest.raises(FileNotFoundError):
        promote_to_trusted("book", vault, hub="20_Power-Electronics", override=True)


def test_unpromote_restores_staging_promotion(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_slug(vault / "91_Ingestion")
    promote_to_staging("book", vault)

    result = unpromote("book", vault)

    assert result.destination == (vault / "91_Ingestion" / "book").resolve(strict=False)
    assert (vault / "91_Ingestion" / "book" / "index.md").exists()
    assert not (vault / "90_Staging" / "book").exists()


def test_unpromote_restores_trusted_promotion_and_frontmatter(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_slug(vault / "90_Staging", selected_hub="20_Power-Electronics")
    (vault / "20_Power-Electronics").mkdir(parents=True)
    promote_to_trusted("book", vault, hub="20_Power-Electronics")

    result = unpromote("book", vault)

    restored = vault / "90_Staging" / "book"
    assert result.destination == restored.resolve(strict=False)
    assert "status: staged" in (restored / "01_chapter.md").read_text(encoding="utf-8")
    assert "trusted_hub:" not in (restored / "01_chapter.md").read_text(encoding="utf-8")


def test_promote_cli_to_staging_and_trusted_hub_requirement(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_slug(vault / "91_Ingestion")
    assert main(["promote", "book", "--vault", str(vault), "--to-staging"]) == 0

    _write_slug(vault / "91_Ingestion", slug="trusted-book", selected_hub="20_Power-Electronics")
    assert main(["promote", "trusted-book", "--vault", str(vault), "--to-trusted"]) == 2
