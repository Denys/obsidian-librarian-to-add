from __future__ import annotations

from pathlib import Path

from obsidian_librarian.pdf_docling import DoclingConversionResult
from obsidian_patron.cli import main


def _fake_conversion() -> DoclingConversionResult:
    return DoclingConversionResult(
        markdown="# Buck converter DSP\n",
        structured_json="{}",
        engine_version="docling-test",
    )


def test_propose_generates_proposal_file(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    pdf = tmp_path / "buck_converter.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "obsidian_patron.docling_pipe.convert_pdf_with_docling",
        lambda _p: _fake_conversion(),
    )

    assert main(["ingest", str(pdf), "--vault", str(vault)]) == 0
    assert main(["propose", "buck-converter", "--vault", str(vault)]) == 0

    proposal = vault / "91_Ingestion" / "buck-converter" / "_proposal.md"
    assert proposal.exists()
    content = proposal.read_text(encoding="utf-8")
    assert "Deterministic classification" in content
    assert "Ranked hub candidates" in content


def test_propose_missing_slug_errors(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    assert main(["propose", "missing", "--vault", str(vault)]) == 2
