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


class FakeInputFormat:
    PDF = "pdf"


class FakePdfPipelineOptions:
    def __init__(self):
        self.enable_remote_services = True
        self.allow_external_plugins = True
        self.do_ocr = True
        self.do_table_structure = False
        self.generate_page_images = True
        self.generate_picture_images = False
        self.do_picture_classification = True
        self.do_picture_description = True


class FakePdfFormatOption:
    def __init__(self, *, pipeline_options):
        self.pipeline_options = pipeline_options


class FakeConverter:
    init_kwargs = None

    def __init__(self, **kwargs):
        type(self).init_kwargs = kwargs

    def convert(self, source):
        return FakeResult()


def patch_fake_docling_pdf_format_api(monkeypatch):
    monkeypatch.setattr(
        pdf_docling,
        "_load_docling_pdf_format_api",
        lambda: pdf_docling.DoclingPdfFormatApi(
            input_format=FakeInputFormat,
            pdf_format_option_cls=FakePdfFormatOption,
            pdf_pipeline_options_cls=FakePdfPipelineOptions,
        ),
    )


def test_convert_pdf_with_docling_uses_lazy_converter(monkeypatch, tmp_path):
    source = tmp_path / "fixture.pdf"
    source.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(pdf_docling, "_load_docling_converter", lambda: FakeConverter)
    patch_fake_docling_pdf_format_api(monkeypatch)
    monkeypatch.setattr(pdf_docling, "_docling_version", lambda: "test-version")

    result = convert_pdf_with_docling(source)

    assert result.markdown.startswith("# Converted")
    assert '"pages": 1' in result.structured_json
    assert result.engine_version == "test-version"
    assert result.tables_json is None


def test_convert_pdf_with_docling_disables_ocr_in_pdf_pipeline_options(
    monkeypatch,
    tmp_path,
):
    source = tmp_path / "fixture.pdf"
    source.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(pdf_docling, "_load_docling_converter", lambda: FakeConverter)
    patch_fake_docling_pdf_format_api(monkeypatch)

    convert_pdf_with_docling(source)

    format_options = FakeConverter.init_kwargs["format_options"]
    pipeline_options = format_options[FakeInputFormat.PDF].pipeline_options
    assert pipeline_options.do_ocr is False
    assert pipeline_options.do_table_structure is True
    assert pipeline_options.generate_picture_images is True
    assert pipeline_options.generate_page_images is False
    assert pipeline_options.enable_remote_services is False
    assert pipeline_options.allow_external_plugins is False
    assert pipeline_options.do_picture_classification is False
    assert pipeline_options.do_picture_description is False


def test_docling_pdf_pipeline_options_require_disable_ocr_support() -> None:
    class MissingOcrPipelineOptions:
        pass

    with pytest.raises(PdfDependencyError, match="cannot guarantee OCR disabled"):
        pdf_docling._build_docling_pdf_pipeline_options(MissingOcrPipelineOptions)


def test_convert_pdf_with_docling_propagates_missing_ocr_switch(
    monkeypatch,
    tmp_path,
) -> None:
    class MissingOcrPipelineOptions:
        pass

    source = tmp_path / "fixture.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(pdf_docling, "_load_docling_converter", lambda: FakeConverter)
    monkeypatch.setattr(
        pdf_docling,
        "_load_docling_pdf_format_api",
        lambda: pdf_docling.DoclingPdfFormatApi(
            input_format=FakeInputFormat,
            pdf_format_option_cls=FakePdfFormatOption,
            pdf_pipeline_options_cls=MissingOcrPipelineOptions,
        ),
    )

    with pytest.raises(PdfDependencyError, match="cannot guarantee OCR disabled"):
        convert_pdf_with_docling(source)


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
        def __init__(self, **kwargs):
            pass

        def convert(self, source):
            return TableResult()

    source = tmp_path / "fixture.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(pdf_docling, "_load_docling_converter", lambda: TableConverter)
    patch_fake_docling_pdf_format_api(monkeypatch)
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
        def __init__(self, **kwargs):
            pass

        def convert(self, source):
            return EmptyResult()

    source = tmp_path / "fixture.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(pdf_docling, "_load_docling_converter", lambda: EmptyConverter)
    patch_fake_docling_pdf_format_api(monkeypatch)

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


class FakePngImage:
    def save(self, filelike, format="PNG"):
        filelike.write(b"\x89PNG\r\n")


def test_extract_docling_assets_none() -> None:
    doc = types.SimpleNamespace()
    assert pdf_docling._extract_docling_assets(doc) == ()


def test_extract_docling_assets_from_bytes() -> None:
    doc = types.SimpleNamespace(images=[types.SimpleNamespace(kind="image", bytes=b"abc", page=1)])
    assets = pdf_docling._extract_docling_assets(doc)
    assert len(assets) == 1
    assert assets[0].relative_path.as_posix() == "page-001-image-001.png"
    assert assets[0].content == b"abc"
    assert assets[0].kind == "image"
    assert assets[0].page_number == 1
    assert assets[0].caption is None


def test_extract_docling_assets_from_pil_like_image() -> None:
    doc = types.SimpleNamespace(
        figures=[
            types.SimpleNamespace(kind="figure", image=FakePngImage(), page_number=2)
        ]
    )
    assets = pdf_docling._extract_docling_assets(doc)
    assert len(assets) == 1
    assert assets[0].relative_path.as_posix() == "page-002-figure-001.png"
    assert assets[0].content.startswith(b"\x89PNG")
    assert assets[0].kind == "figure"
    assert assets[0].page_number == 2


def test_extract_docling_assets_from_get_image_with_caption_and_provenance() -> None:
    class DoclingPictureLike:
        kind = "figure"
        prov = [types.SimpleNamespace(page_no=3)]

        def get_image(self, document):
            assert document is doc
            return FakePngImage()

        def caption_text(self, document):
            assert document is doc
            return "Schematic overview"

    doc = types.SimpleNamespace(pictures=[DoclingPictureLike()])

    assets = pdf_docling._extract_docling_assets(doc)

    assert len(assets) == 1
    assert assets[0].relative_path.as_posix() == "page-003-figure-001.png"
    assert assets[0].content.startswith(b"\x89PNG")
    assert assets[0].kind == "figure"
    assert assets[0].page_number == 3
    assert assets[0].caption == "Schematic overview"


def test_safe_asset_name_rejects_unsafe_candidate_name() -> None:
    candidate = types.SimpleNamespace(kind="figure", name="../evil.png")
    asset_name = pdf_docling._safe_asset_name(candidate, 1)
    assert ".." not in asset_name.as_posix()
    assert not asset_name.is_absolute()


def test_extract_docling_assets_multiple_are_deterministic() -> None:
    doc = types.SimpleNamespace(
        figures=[
            types.SimpleNamespace(kind="figure", bytes=b"1"),
            types.SimpleNamespace(kind="figure", bytes=b"2"),
        ]
    )
    assets = pdf_docling._extract_docling_assets(doc)
    assert [a.relative_path.as_posix() for a in assets] == ["figure-001.png", "figure-002.png"]
