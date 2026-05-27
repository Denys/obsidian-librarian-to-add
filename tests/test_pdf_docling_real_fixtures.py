from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from obsidian_librarian.ingest import ingest_inbox
from obsidian_librarian.validators import validate_path

DOCILING = pytest.importorskip("docling")

FIXTURE_ROOT = Path("fixtures/pdf")


def skip_if_missing_fixture(filename: str) -> None:
    if not (FIXTURE_ROOT / filename).is_file():
        pytest.skip(f"optional copied PDF fixture missing: {filename}")


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
    skip_if_missing_fixture(filename)
    target = inbox / filename
    shutil.copy2(source, target)

    result = ingest_inbox(inbox, tmp_path, mode="draft", include_pdf=True, pdf_converter="docling")
    manifest = result.pdf_manifests[0]
    assert manifest.outputs.root is not None
    staging_root = tmp_path / "90_Staging" / manifest.outputs.root

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


def test_docling_table_heavy_fixture_quality_gates(tmp_path: Path) -> None:
    filename = "table-heavy-electrical-spec.pdf"
    skip_if_missing_fixture(filename)
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    shutil.copy2(FIXTURE_ROOT / filename, inbox / filename)

    result = ingest_inbox(inbox, tmp_path, mode="draft", include_pdf=True, pdf_converter="docling")
    manifest = result.pdf_manifests[0]
    staging_root = tmp_path / "90_Staging" / manifest.outputs.root
    tables_path = staging_root / "tables.json"
    source_md = (staging_root / "source.md").read_text(encoding="utf-8")
    tables_text = tables_path.read_text(encoding="utf-8")

    assert manifest.extraction.ocr_enabled is False
    assert manifest.outputs.table_sidecars
    assert tables_path.is_file()
    assert '"tables": [' in tables_text
    assert "Parameter" in source_md
    assert "[tables.json](tables.json)" in source_md

    validation = validate_path(tmp_path / "90_Staging")
    assert validation.passed is True


@pytest.mark.parametrize(
    "filename",
    [
        "app-note-mixed-layout.pdf",
        "2 Classification of PV Power Systems - PV PS -- modelling design control.pdf",
        "A comprehensive techno-economic review of microinverters.pdf",
    ],
)
def test_docling_diagram_fixture_asset_quality_gates(
    tmp_path: Path,
    filename: str,
) -> None:
    skip_if_missing_fixture(filename)
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    shutil.copy2(FIXTURE_ROOT / filename, inbox / filename)

    result = ingest_inbox(inbox, tmp_path, mode="draft", include_pdf=True, pdf_converter="docling")
    manifest = result.pdf_manifests[0]
    staging_root = tmp_path / "90_Staging" / manifest.outputs.root
    source_md = (staging_root / "source.md").read_text(encoding="utf-8").lower()

    assert manifest.extraction.ocr_enabled is False
    assert manifest.outputs.asset_dir is not None
    asset_dir = tmp_path / "90_Staging" / manifest.outputs.asset_dir
    assert asset_dir.is_dir()
    assert any(path.is_file() for path in asset_dir.rglob("*"))
    assert "[docling.json](docling.json)" in source_md
    assert "(assets/" in source_md

    validation = validate_path(tmp_path / "90_Staging")
    assert validation.passed is True
