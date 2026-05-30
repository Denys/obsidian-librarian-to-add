from __future__ import annotations

import sys
import types
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
    trusted = vault / "20_Power-Electronics"
    trusted.mkdir()
    (trusted / "Buck.md").write_text("# Buck\n\n#power #converter\n", encoding="utf-8")
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
    assert "selected_hub: 20_Power-Electronics" in content
    assert "Ranked hub candidates" in content
    assert "- converter" in content


def test_propose_llm_degrades_without_key(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    pdf = tmp_path / "mystery.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "obsidian_patron.docling_pipe.convert_pdf_with_docling",
        lambda _p: _fake_conversion(),
    )

    assert main(["ingest", str(pdf), "--vault", str(vault)]) == 0
    assert main(["propose", "mystery", "--vault", str(vault), "--llm"]) == 0

    content = (vault / "91_Ingestion" / "mystery" / "_proposal.md").read_text(
        encoding="utf-8"
    )
    assert "LLM enrichment skipped" in content


def test_propose_llm_success_is_written_only_to_proposal(
    tmp_path: Path, monkeypatch
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    pdf = tmp_path / "llm.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "obsidian_patron.docling_pipe.convert_pdf_with_docling",
        lambda _p: _fake_conversion(),
    )

    class FakeResponses:
        def create(self, **_kwargs):
            return types.SimpleNamespace(
                output_text=(
                    "### suggested_hub\n"
                    "20_Power-Electronics\n\n"
                    "### abstract\n"
                    "Mock LLM summary for review only.\n\n"
                    "### llm_suggested_tags\n"
                    "- llm_suggested: power-stage"
                )
            )

    class FakeOpenAI:
        def __init__(self):
            self.responses = FakeResponses()

    monkeypatch.setitem(
        sys.modules,
        "openai",
        types.SimpleNamespace(OpenAI=FakeOpenAI),
    )

    assert main(["ingest", str(pdf), "--vault", str(vault)]) == 0
    assert main(["propose", "llm", "--vault", str(vault), "--llm"]) == 0

    slug_dir = vault / "91_Ingestion" / "llm"
    proposal = (slug_dir / "_proposal.md").read_text(encoding="utf-8")
    section_note = (slug_dir / "01_buck-converter-dsp.md").read_text(encoding="utf-8")
    assert "## LLM enrichment" in proposal
    assert "llm_suggested: power-stage" in proposal
    assert "Mock LLM summary" not in section_note


def test_propose_missing_slug_errors(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    assert main(["propose", "missing", "--vault", str(vault)]) == 2
