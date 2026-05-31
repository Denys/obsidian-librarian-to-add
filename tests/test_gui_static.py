from __future__ import annotations

from pathlib import Path

HTML = Path("src/obsidian_librarian/gui/static/index.html").read_text(encoding="utf-8")


def test_static_gui_contains_required_pages_and_safety_labels() -> None:
    for label in ["Dashboard", "Ingest", "Validate", "Search", "Reports", "Patron", "Settings"]:
        assert label in HTML

    for label in ["Read-only", "Staging Write", "Patron Ingestion", "Promotion"]:
        assert label in HTML

    assert "Command Preview" in HTML
    assert "Safety Patch Panel" in HTML
    assert "Explicit Options" in HTML
    assert "OCR" in HTML
    assert "LLM" in HTML


def test_static_gui_has_no_external_assets() -> None:
    assert "<script src=" not in HTML
    assert "<link href=" not in HTML
    assert "fonts.googleapis" not in HTML
    assert "cdn" not in HTML.lower()
