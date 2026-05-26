from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from obsidian_librarian.ingest import ingest_inbox
from obsidian_librarian.validators import validate_path

DOCILING = pytest.importorskip("docling")

FIXTURE_ROOT = Path("fixtures/pdf")

@pytest.mark.parametrize(
    "filename,required_terms,allow_missing_assets",
    [
        ("digital-basic.pdf", ["Sentinel"], False),
        ("table-heavy-electrical-spec.pdf", ["Parameter"], False),
        ("A comprehensive techno-economic review of microinverters.pdf", ["microinverter"], True),
    ],
)
def test_docling_real_fixture_smoke(
    tmp_path: Path,
    filename: str,
    required_terms: list[str],
    allow_missing_assets: bool,
) -> None:
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    source = FIXTURE_ROOT / filename
    target = inbox / filename
    shutil.copy2(source, target)

    result = ingest_inbox(inbox, tmp_path, mode="draft", include_pdf=True, pdf_converter="docling")
    manifest = result.pdf_manifests[0]
    stem = Path(filename).stem
    staging_root = tmp_path / "90_Staging" / "pdf" / stem

    assert (staging_root / "manifest.json").is_file()
    assert (staging_root / "source.md").is_file()
    assert (staging_root / "docling.json").is_file()

    validation = validate_path(tmp_path / "90_Staging")
    assert validation.passed is True

    source_md = (staging_root / "source.md").read_text(encoding="utf-8").lower()
    for term in required_terms:
        assert term.lower() in source_md

    if allow_missing_assets:
        if manifest.outputs.asset_dir:
            asset_dir = tmp_path / "90_Staging" / manifest.outputs.asset_dir
            assert asset_dir.is_dir()
            assert any(asset_dir.iterdir())
    elif manifest.outputs.asset_dir:
        asset_dir = tmp_path / "90_Staging" / manifest.outputs.asset_dir
        assert asset_dir.is_dir()
