from __future__ import annotations

import types

import pytest

from obsidian_librarian import pdf_docling
from obsidian_librarian.pdf_docling import (
    PdfConversionError,
    PdfDependencyError,
    convert_pdf_with_docling,
)


class FakeDocument:
    def export_to_markdown(self):
        return "# Converted\n\nSentinel-A"

    def export_to_dict(self):
        return {"pages": 1, "text": "Sentinel-A"}


class FakeResult:
    document = FakeDocument()


class FakeConverter:
    def convert(self, source):
        return FakeResult()


def test_convert_pdf_with_docling_uses_lazy_converter(monkeypatch, tmp_path):
    source = tmp_path / "fixture.pdf"
    source.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(pdf_docling, "_load_docling_converter", lambda: FakeConverter)
    monkeypatch.setattr(pdf_docling, "_docling_version", lambda: "test-version")

    result = convert_pdf_with_docling(source)

    assert result.markdown.startswith("# Converted")
    assert '"pages": 1' in result.structured_json
    assert result.engine_version == "test-version"
    assert result.tables_json is None


def test_convert_pdf_with_docling_exports_table_sidecar_when_payload_has_tables(
    monkeypatch,
    tmp_path,
):
    class TableDocument:
        def export_to_markdown(self):
            return "# Converted\n\nElectrical table extracted."

        def export_to_dict(self):
            return {
                "body": {
                    "tables": [
                        {"cells": [["voltage", "current"], ["30V", "5A"]]},
                    ],
                }
            }

    class TableResult:
        document = TableDocument()

    class TableConverter:
        def convert(self, source):
            return TableResult()

    source = tmp_path / "fixture.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(pdf_docling, "_load_docling_converter", lambda: TableConverter)
    monkeypatch.setattr(pdf_docling, "_docling_version", lambda: "test-version")

    result = convert_pdf_with_docling(source)

    assert result.tables_json is not None
    assert '"schema_version": 1' in result.tables_json
    assert '"source": "docling_structured_export"' in result.tables_json
    assert '"path": "$.body.tables"' in result.tables_json


def test_convert_pdf_with_docling_rejects_empty_markdown(monkeypatch, tmp_path):
    class EmptyDocument:
        def export_to_markdown(self):
            return "\n"

    class EmptyResult:
        document = EmptyDocument()

    class EmptyConverter:
        def convert(self, source):
            return EmptyResult()

    source = tmp_path / "fixture.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(pdf_docling, "_load_docling_converter", lambda: EmptyConverter)

    with pytest.raises(PdfConversionError, match="empty Markdown"):
        convert_pdf_with_docling(source)


def test_load_docling_converter_missing_dependency(monkeypatch):
    def fail_import(name):
        raise ImportError(name)

    monkeypatch.setattr(pdf_docling, "import_module", fail_import)

    with pytest.raises(PdfDependencyError, match="optional PDF support"):
        pdf_docling._load_docling_converter()


def test_load_docling_converter_missing_class(monkeypatch):
    monkeypatch.setattr(pdf_docling, "import_module", lambda name: types.SimpleNamespace())

    with pytest.raises(PdfDependencyError, match="DocumentConverter"):
        pdf_docling._load_docling_converter()
