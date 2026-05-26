from __future__ import annotations

from pathlib import Path

import pytest

from obsidian_librarian.pdf_fixtures import load_pdf_fixtures


def test_load_pdf_fixtures_happy_path(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures" / "pdf"
    fixtures_dir.mkdir(parents=True)
    (fixtures_dir / "sample.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
    (fixtures_dir / "fixtures.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "fixture_root: fixtures/pdf",
                "fixtures:",
                "  - id: basic",
                "    file: sample.pdf",
                "    role: baseline",
                "    phase_11_1:",
                "      expected_status: staged",
                "      expected_classification: digital_pdf",
                "    phase_11_2:",
                "      should_convert: false",
            ]
        ),
        encoding="utf-8",
    )

    loaded = load_pdf_fixtures(fixtures_dir / "fixtures.yaml")

    assert len(loaded) == 1
    assert loaded[0].id == "basic"
    assert loaded[0].file == Path("sample.pdf")


def test_load_pdf_fixtures_rejects_duplicate_ids(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures" / "pdf"
    fixtures_dir.mkdir(parents=True)
    (fixtures_dir / "sample.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
    (fixtures_dir / "fixtures.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "fixture_root: fixtures/pdf",
                "fixtures:",
                "  - id: duplicate",
                "    file: sample.pdf",
                "    role: baseline",
                "  - id: duplicate",
                "    file: sample.pdf",
                "    role: baseline",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate fixture id"):
        load_pdf_fixtures(fixtures_dir / "fixtures.yaml")
