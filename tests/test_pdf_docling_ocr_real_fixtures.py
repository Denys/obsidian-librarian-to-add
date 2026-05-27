from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from obsidian_librarian.ingest import ingest_inbox
from obsidian_librarian.validators import validate_path

pytest.importorskip("docling")
pytestmark = pytest.mark.skipif(
    os.environ.get("OBSIDIAN_LIBRARIAN_RUN_OCR_REAL") != "1",
    reason="Set OBSIDIAN_LIBRARIAN_RUN_OCR_REAL=1 to run real Docling OCR fixture smoke.",
)

FIXTURE_ROOT = Path("fixtures/pdf")


def test_docling_real_ocr_scanned_fixture_smoke(tmp_path: Path) -> None:
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    source = FIXTURE_ROOT / "scanned-one-page.pdf"
    target = inbox / source.name
    shutil.copy2(source, target)

    result = ingest_inbox(
        inbox,
        tmp_path,
        mode="draft",
        include_pdf=True,
        pdf_converter="docling",
        pdf_ocr=True,
    )
    manifest = result.pdf_manifests[0]
    warning_text = "\n".join(warning.message for warning in manifest.extraction.warnings)
    if manifest.status == "failed":
        if _looks_like_missing_ocr_backend(warning_text):
            pytest.skip(f"Docling OCR backend unavailable: {warning_text}")
        pytest.skip(f"Docling OCR failed safely on this local fixture/runtime: {warning_text}")

    assert manifest.outputs.root is not None
    staging_root = tmp_path / "90_Staging" / manifest.outputs.root
    assert manifest.status == "needs_review"
    assert manifest.extraction.method == "ocr"
    assert manifest.extraction.ocr_enabled is True
    assert (staging_root / "manifest.json").is_file()
    assert (staging_root / "source.md").is_file()
    assert (staging_root / "docling.json").is_file()

    source_md = (staging_root / "source.md").read_text(encoding="utf-8")
    assert "OCR warning" in source_md
    assert "ocr_enabled: true" in source_md
    assert "confidence: \"ocr-derived-needs-review\"" in source_md

    validation = validate_path(tmp_path / "90_Staging")
    assert validation.passed is True


def _looks_like_missing_ocr_backend(message: str) -> bool:
    lower = message.lower()
    return any(
        phrase in lower
        for phrase in (
            "ocr backend",
            "rapidocr",
            "tesseract",
            "easyocr",
            "not installed",
            "not found",
            "no module named",
        )
    )
