"""Optional Docling PDF conversion adapter for Phase 11.2+11.4."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import import_module, metadata
from io import BytesIO
from pathlib import Path
from typing import Any


class PdfConversionError(RuntimeError):
    """Raised when PDF conversion fails safely."""


class PdfDependencyError(PdfConversionError):
    """Raised when the optional Docling dependency is missing."""


@dataclass(frozen=True)
class DoclingAsset:
    """One staged binary/text asset exported by a PDF converter."""

    relative_path: Path
    content: bytes
    kind: str | None = None
    page_number: int | None = None
    caption: str | None = None


@dataclass(frozen=True)
class DoclingConversionResult:
    """Docling conversion output needed by the staging writer."""

    markdown: str
    structured_json: str
    engine_version: str
    tables_json: str | None = None
    assets: tuple[DoclingAsset, ...] = ()


@dataclass(frozen=True)
class DoclingPdfFormatApi:
    """Docling classes needed to configure PDF conversion without eager imports."""

    input_format: Any
    pdf_format_option_cls: type[Any]
    pdf_pipeline_options_cls: type[Any]


def convert_pdf_with_docling(path: str | Path) -> DoclingConversionResult:
    """Convert a PDF with Docling and return Markdown plus structured sidecars."""
    pdf_path = Path(path).expanduser().resolve(strict=False)
    converter_cls = _load_docling_converter()

    try:
        converter = _build_docling_converter(converter_cls)
    except PdfDependencyError:
        raise
    except Exception as exc:
        raise PdfConversionError(f"Docling converter setup failed for {pdf_path}: {exc}") from exc

    try:
        result = converter.convert(pdf_path)
        document = result.document
        markdown = document.export_to_markdown()
        structured_payload = _export_docling_payload(document)
        structured = _json_dumps(structured_payload)
        tables_json = _export_docling_tables_json(structured_payload)
        assets = _extract_docling_assets(document)
    except Exception as exc:
        raise PdfConversionError(f"Docling conversion failed for {pdf_path}: {exc}") from exc

    if not markdown.strip():
        raise PdfConversionError(f"Docling produced empty Markdown for {pdf_path}")

    return DoclingConversionResult(
        markdown=markdown,
        structured_json=structured,
        engine_version=_docling_version(),
        tables_json=tables_json,
        assets=assets,
    )


def _build_docling_converter(converter_cls: type[Any]) -> Any:
    api = _load_docling_pdf_format_api()
    pipeline_options = _build_docling_pdf_pipeline_options(api.pdf_pipeline_options_cls)
    pdf_format_option = api.pdf_format_option_cls(pipeline_options=pipeline_options)
    return converter_cls(format_options={api.input_format.PDF: pdf_format_option})


def _extract_docling_assets(document: Any) -> tuple[DoclingAsset, ...]:
    candidates = list(_iter_docling_asset_candidates(document))
    assets: list[DoclingAsset] = []
    for index, candidate in enumerate(candidates, start=1):
        payload = _asset_bytes(candidate, document)
        if not payload:
            continue
        assets.append(
            DoclingAsset(
                relative_path=_safe_asset_name(candidate, index),
                content=payload,
                kind=_asset_kind(candidate),
                page_number=_asset_page(candidate),
                caption=_asset_caption(candidate, document),
            )
        )
    return tuple(assets)


def _iter_docling_asset_candidates(document: Any):
    for attr in ("pictures", "images", "figures", "elements", "pages"):
        value = getattr(document, attr, None)
        yield from _iter_candidate_values(value)


def _iter_candidate_values(value: Any):
    if value is None:
        return
    if isinstance(value, dict):
        for child in value.values():
            yield from _iter_candidate_values(child)
        return
    if isinstance(value, (list, tuple, set)):
        for child in value:
            yield from _iter_candidate_values(child)
        return
    yield value


def _asset_bytes(candidate: Any, document: Any) -> bytes | None:
    for key in ("content", "bytes", "data", "image_bytes"):
        raw = getattr(candidate, key, None)
        if isinstance(raw, bytes) and raw:
            return raw

    image = getattr(candidate, "image", None) or getattr(candidate, "pil_image", None)
    payload = _image_to_png_bytes(image)
    if payload:
        return payload

    get_image = getattr(candidate, "get_image", None)
    if callable(get_image):
        try:
            image = get_image(document)
        except Exception:
            image = None
        payload = _image_to_png_bytes(image)
        if payload:
            return payload

    pathish = getattr(candidate, "path", None) or getattr(candidate, "file", None)
    if isinstance(pathish, (str, Path)):
        path = Path(pathish).expanduser()
        if path.is_absolute() and path.is_file():
            try:
                return path.read_bytes()
            except OSError:
                return None

    return None


def _image_to_png_bytes(image: Any) -> bytes | None:
    if image is None or not hasattr(image, "save"):
        return None
    output = BytesIO()
    try:
        image.save(output, format="PNG")
    except Exception:
        return None
    payload = output.getvalue()
    return payload if payload else None


def _safe_asset_name(candidate: Any, index: int) -> Path:
    kind = _asset_kind(candidate) or "image"
    page = _asset_page(candidate)
    stem = f"{kind}-{index:03d}.png"
    if page is not None and page > 0:
        stem = f"page-{page:03d}-{kind}-{index:03d}.png"
    return Path(stem)


def _asset_kind(candidate: Any) -> str:
    label = str(
        getattr(candidate, "kind", None) or getattr(candidate, "label", None) or ""
    ).lower()
    if "figure" in label or "picture" in label:
        return "figure"
    if "image" in label:
        return "image"
    if hasattr(candidate, "caption") or hasattr(candidate, "caption_text"):
        return "figure"
    return "image"


def _asset_page(candidate: Any) -> int | None:
    for key in ("page", "page_no", "page_number"):
        value = getattr(candidate, key, None)
        if isinstance(value, int) and value > 0:
            return value
        if isinstance(value, str) and value.isdigit() and int(value) > 0:
            return int(value)
    prov = getattr(candidate, "prov", None)
    if isinstance(prov, (list, tuple)) and prov:
        return _asset_page(prov[0])
    if prov is not None:
        return _asset_page(prov)
    return None


def _asset_caption(candidate: Any, document: Any) -> str | None:
    caption_text = getattr(candidate, "caption_text", None)
    if callable(caption_text):
        try:
            caption = str(caption_text(document)).strip()
        except Exception:
            caption = ""
        if caption:
            return caption

    for key in ("caption", "text", "title"):
        caption = getattr(candidate, key, None)
        if isinstance(caption, str) and caption.strip():
            return caption.strip()

    captions = getattr(candidate, "captions", None)
    if isinstance(captions, (list, tuple)) and captions:
        first = captions[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
        text = getattr(first, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
    return None


def _load_docling_converter() -> type[Any]:
    try:
        module = import_module("docling.document_converter")
    except ImportError as exc:
        raise PdfDependencyError(
            "Install optional PDF support with: pip install -e .[pdf]"
        ) from exc

    try:
        return module.DocumentConverter
    except AttributeError as exc:
        raise PdfDependencyError(
            "Installed docling package does not expose DocumentConverter"
        ) from exc


def _load_docling_pdf_format_api() -> DoclingPdfFormatApi:
    try:
        converter_module = import_module("docling.document_converter")
        pipeline_options_module = import_module("docling.datamodel.pipeline_options")
        base_models_module = import_module("docling.datamodel.base_models")
    except ImportError as exc:
        raise PdfDependencyError(
            "Install optional PDF support with: pip install -e .[pdf]"
        ) from exc

    try:
        return DoclingPdfFormatApi(
            input_format=base_models_module.InputFormat,
            pdf_format_option_cls=converter_module.PdfFormatOption,
            pdf_pipeline_options_cls=pipeline_options_module.PdfPipelineOptions,
        )
    except AttributeError as exc:
        raise PdfDependencyError(
            "Installed docling package does not expose configurable PDF pipeline options"
        ) from exc


def _build_docling_pdf_pipeline_options(pdf_pipeline_options_cls: type[Any]) -> Any:
    options = pdf_pipeline_options_cls()
    _set_required_docling_option(options, "do_ocr", False)
    _set_optional_docling_options(
        options,
        {
            "enable_remote_services": False,
            "allow_external_plugins": False,
            "do_table_structure": True,
            "generate_page_images": False,
            "generate_picture_images": True,
            "do_picture_classification": False,
            "do_picture_description": False,
            "do_chart_extraction": False,
            "do_code_enrichment": False,
            "do_formula_enrichment": False,
            "force_backend_text": False,
        },
    )
    if getattr(options, "do_ocr", None) is not False:
        raise PdfDependencyError(
            "Installed docling package cannot guarantee OCR disabled for PDF conversion"
        )
    return options


def _set_required_docling_option(options: Any, name: str, value: Any) -> None:
    if not _supports_docling_option(options, name):
        raise PdfDependencyError(
            "Installed docling package cannot guarantee OCR disabled for PDF conversion"
        )
    setattr(options, name, value)


def _set_optional_docling_options(options: Any, values: dict[str, Any]) -> None:
    for name, value in values.items():
        if _supports_docling_option(options, name):
            setattr(options, name, value)


def _supports_docling_option(options: Any, name: str) -> bool:
    fields = getattr(type(options), "model_fields", None) or getattr(
        type(options), "__fields__", None
    )
    if fields is not None:
        return name in fields
    return hasattr(options, name)


def _docling_version() -> str:
    try:
        return metadata.version("docling")
    except metadata.PackageNotFoundError:
        return "unknown"


def _export_docling_json(document: Any) -> str:
    """Export Docling document JSON for backward-compatible direct callers."""
    return _json_dumps(_export_docling_payload(document))


def _export_docling_payload(document: Any) -> Any:
    for method_name in ("export_to_dict", "model_dump"):
        method = getattr(document, method_name, None)
        if callable(method):
            return method()

    return {"repr": repr(document)}


def _export_docling_tables_json(payload: Any) -> str | None:
    """Export table-like structures as a deterministic sidecar when present.

    This is a structural preservation sidecar, not a semantic table-quality score.
    It records table-like payloads found in Docling's structured export so later
    phases can add quality gates without flattening tables into prose.
    """
    tables = _collect_table_like_payloads(payload)
    if not tables:
        return None
    return _json_dumps(
        {
            "schema_version": 1,
            "source": "docling_structured_export",
            "tables": tables,
        }
    )


def _collect_table_like_payloads(payload: Any, path: str = "$") -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}"
            if key.lower() in {"tables", "table"} and value:
                tables.append({"path": child_path, "payload": value})
                continue
            tables.extend(_collect_table_like_payloads(value, child_path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            tables.extend(_collect_table_like_payloads(value, f"{path}[{index}]"))
    return tables


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
