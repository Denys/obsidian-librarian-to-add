from __future__ import annotations

import json
from pathlib import Path

from obsidian_librarian.pdf_docling import DoclingConversionResult
from obsidian_patron.cli import main


def test_patron_ingest_requires_existing_pdf(tmp_path: Path, capsys) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    exit_code = main(["ingest", str(tmp_path / "missing.pdf"), "--vault", str(vault)])
    assert exit_code == 2
    assert "Error:" in capsys.readouterr().out


def test_patron_ingest_force_archives_previous(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n")

    def fake_convert(_path: str | Path) -> DoclingConversionResult:
        return DoclingConversionResult(
            markdown="# Converted\n",
            structured_json="{}",
            engine_version="docling-test",
        )

    monkeypatch.setattr("obsidian_patron.docling_pipe.convert_pdf_with_docling", fake_convert)
    assert main(["ingest", str(pdf), "--vault", str(vault)]) == 0
    assert main(["ingest", str(pdf), "--vault", str(vault), "--force"]) == 0
    out_dir = vault / "91_Ingestion" / "source"
    assert out_dir.exists()
    assert (vault / "91_Ingestion" / "_archive" / "source").exists()
    manifest = json.loads((out_dir / "_ingest_manifest.json").read_text(encoding="utf-8"))
    assert manifest["document_type"] == "pdf"
