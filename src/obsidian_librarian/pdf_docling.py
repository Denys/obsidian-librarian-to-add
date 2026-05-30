"""Optional Docling PDF conversion adapter for Phase 11.2+11.4."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from importlib import import_module, metadata
from io import BytesIO
from pathlib import Path
from typing import Any


class PdfConversionError(RuntimeError):
    """Raised when PDF conversion fails safely."""


class PdfDependencyError(PdfConversionError):
    """Raised when the optional Docling dependency is missing."""


@dataclass(frozen=True)
class DoclingSection:
    """One logical document section preserved from Docling or Markdown structure."""

    title: str
    markdown: str
    heading_path: str | None = None
    level: int = 1
    children: tuple[DoclingSection, ...] = ()
    kind: str | None = None


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
    sections: tuple[DoclingSection, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    tables: tuple[dict[str, Any], ...] = ()
    code_blocks: tuple[str, ...] = ()
    figure_captions: tuple[str, ...] = ()
    glossary_index_hints: tuple[str, ...] = ()


@dataclass(frozen=True)
class DoclingPdfFormatApi:
    """Docling classes needed to configure PDF conversion without eager imports."""

    input_format: Any
    pdf_format_option_cls: type[Any]
    pdf_pipeline_options_cls: type[Any]
    ocr_options_cls: type[Any] | None = None


def convert_pdf_with_docling(path: str | Path) -> DoclingConversionResult:
    """Convert a PDF with Docling and return Markdown plus structured sidecars."""
    return _convert_pdf_with_docling_converter(path, build_ocr_converter=False)


def convert_pdf_with_docling_ocr(path: str | Path) -> DoclingConversionResult:
    """Convert a scanned PDF with explicit Docling OCR enabled."""
    return _convert_pdf_with_docling_converter(path, build_ocr_converter=True)


def _convert_pdf_with_docling_converter(
    path: str | Path,
    *,
    build_ocr_converter: bool,
) -> DoclingConversionResult:
    pdf_path = Path(path).expanduser().resolve(strict=False)
    converter_cls = _load_docling_converter()

    try:
        if build_ocr_converter:
            converter = _build_docling_ocr_converter(converter_cls)
        else:
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
        tables = tuple(_collect_table_like_payloads(structured_payload))
        tables_json = _export_docling_tables_json_from_tables(list(tables))
        assets = _extract_docling_assets(document)
        sections = _extract_docling_sections(markdown, structured_payload)
        metadata_payload = _extract_docling_metadata(document, structured_payload)
        code_blocks = _extract_docling_code_blocks(markdown, structured_payload)
        figure_captions = _extract_docling_figure_captions(assets, structured_payload)
        glossary_index_hints = _extract_glossary_index_hints(sections, structured_payload)
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
        sections=sections,
        metadata=metadata_payload,
        tables=tables,
        code_blocks=code_blocks,
        figure_captions=figure_captions,
        glossary_index_hints=glossary_index_hints,
    )


def _build_docling_converter(converter_cls: type[Any]) -> Any:
    api = _load_docling_pdf_format_api()
    pipeline_options = _build_docling_pdf_pipeline_options(api.pdf_pipeline_options_cls)
    pdf_format_option = api.pdf_format_option_cls(pipeline_options=pipeline_options)
    return converter_cls(format_options={api.input_format.PDF: pdf_format_option})


def _build_docling_ocr_converter(converter_cls: type[Any]) -> Any:
    api = _load_docling_pdf_format_api()
    pipeline_options = _build_docling_ocr_pdf_pipeline_options(
        api.pdf_pipeline_options_cls,
        api.ocr_options_cls,
    )
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
            ocr_options_cls=getattr(pipeline_options_module, "OcrAutoOptions", None),
        )
    except AttributeError as exc:
        raise PdfDependencyError(
            "Installed docling package does not expose configurable PDF pipeline options"
        ) from exc


def _build_docling_pdf_pipeline_options(pdf_pipeline_options_cls: type[Any]) -> Any:
    options = pdf_pipeline_options_cls()
    _set_required_docling_option(
        options,
        "do_ocr",
        False,
        "Installed docling package cannot guarantee OCR disabled for PDF conversion",
    )
    _harden_docling_pipeline_options(options)
    if getattr(options, "do_ocr", None) is not False:
        raise PdfDependencyError(
            "Installed docling package cannot guarantee OCR disabled for PDF conversion"
        )
    return options


def _build_docling_ocr_pdf_pipeline_options(
    pdf_pipeline_options_cls: type[Any],
    ocr_options_cls: type[Any] | None = None,
) -> Any:
    options = pdf_pipeline_options_cls()
    _set_required_docling_option(
        options,
        "do_ocr",
        True,
        "Installed docling package cannot guarantee OCR enabled for PDF conversion",
    )
    _harden_docling_pipeline_options(options)
    if ocr_options_cls is not None and _supports_docling_option(options, "ocr_options"):
        options.ocr_options = ocr_options_cls(lang=["en"], force_full_page_ocr=True)
    if getattr(options, "do_ocr", None) is not True:
        raise PdfDependencyError(
            "Installed docling package cannot guarantee OCR enabled for PDF conversion"
        )
    return options


def _harden_docling_pipeline_options(options: Any) -> None:
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


def _set_required_docling_option(
    options: Any,
    name: str,
    value: Any,
    error_message: str,
) -> None:
    if not _supports_docling_option(options, name):
        raise PdfDependencyError(error_message)
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
    return _export_docling_tables_json_from_tables(_collect_table_like_payloads(payload))


def _export_docling_tables_json_from_tables(tables: list[dict[str, Any]]) -> str | None:
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


def _extract_docling_metadata(document: Any, payload: Any) -> dict[str, Any]:
    metadata_payload: dict[str, Any] = {}
    for key in ("metadata", "meta", "origin", "document", "properties"):
        value = getattr(document, key, None)
        if isinstance(value, dict):
            metadata_payload.update(value)
        elif value is not None and not callable(value):
            dumped = _object_to_public_dict(value)
            if dumped:
                metadata_payload.update(dumped)

    if isinstance(payload, dict):
        for key in ("metadata", "meta", "origin", "properties"):
            value = payload.get(key)
            if isinstance(value, dict):
                metadata_payload.update(value)

    return _select_metadata_fields(metadata_payload)


def _object_to_public_dict(value: Any) -> dict[str, Any]:
    for method_name in ("model_dump", "dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            dumped = method()
            if isinstance(dumped, dict):
                return dumped
    if hasattr(value, "__dict__"):
        return {k: v for k, v in vars(value).items() if not k.startswith("_")}
    return {}


def _select_metadata_fields(payload: dict[str, Any]) -> dict[str, Any]:
    wanted = {
        "author",
        "authors",
        "creator",
        "date",
        "isbn",
        "keywords",
        "producer",
        "publication_year",
        "subject",
        "title",
        "year",
    }
    selected: dict[str, Any] = {}
    for key, value in payload.items():
        normalized = str(key).strip().lower().replace(" ", "_").replace("-", "_")
        if normalized in wanted and value not in (None, "", [], {}):
            selected[normalized] = value
    return selected


def _extract_docling_sections(markdown: str, payload: Any) -> tuple[DoclingSection, ...]:
    structured = _extract_structured_sections(payload)
    if structured:
        return structured
    return _split_markdown_top_level_sections(markdown)


def _extract_structured_sections(payload: Any) -> tuple[DoclingSection, ...]:
    if not isinstance(payload, dict):
        return ()
    for key in ("sections", "chapters"):
        value = payload.get(key)
        sections = _coerce_sections(value)
        if sections:
            return sections
    body = payload.get("body")
    if isinstance(body, dict):
        for key in ("sections", "chapters"):
            sections = _coerce_sections(body.get(key))
            if sections:
                return sections
    return ()


def _coerce_sections(value: Any) -> tuple[DoclingSection, ...]:
    if not isinstance(value, list):
        return ()
    sections: list[DoclingSection] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("heading") or item.get("name")
        text = item.get("markdown") or item.get("text") or item.get("content") or ""
        if not isinstance(title, str) or not title.strip():
            continue
        children = _coerce_sections(item.get("children") or item.get("sections"))
        level = item.get("level", 1)
        if not isinstance(level, int):
            level = 1
        kind = item.get("kind") if isinstance(item.get("kind"), str) else None
        heading_path = item.get("heading_path") or item.get("path") or title.strip()
        if not isinstance(heading_path, str):
            heading_path = title.strip()
        markdown = str(text).strip()
        if not markdown.startswith("#"):
            markdown = f"{'#' * max(level, 1)} {title.strip()}\n\n{markdown}".strip()
        sections.append(
            DoclingSection(
                title=title.strip(),
                markdown=markdown + "\n",
                heading_path=heading_path.strip(),
                level=max(level, 1),
                children=children,
                kind=kind,
            )
        )
    return tuple(sections)


def _split_markdown_top_level_sections(markdown: str) -> tuple[DoclingSection, ...]:
    lines = markdown.strip().splitlines()
    sections: list[DoclingSection] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in lines:
        match = re.match(r"^(#{1,2})\s+(.+?)\s*$", line)
        if match and len(match.group(1)) == 1:
            if current_title is not None:
                sections.append(
                    DoclingSection(
                        title=current_title,
                        markdown="\n".join(current_lines).strip() + "\n",
                    )
                )
            current_title = match.group(2).strip()
            current_lines = [line]
        else:
            if current_title is None:
                current_title = "Document"
                current_lines = ["# Document", ""]
            current_lines.append(line)

    if current_title is not None:
        sections.append(
            DoclingSection(
                title=current_title,
                markdown="\n".join(current_lines).strip() + "\n",
            )
        )
    return tuple(sections)


def _extract_docling_code_blocks(markdown: str, payload: Any) -> tuple[str, ...]:
    blocks = [
        match.group(1).strip()
        for match in re.finditer(r"```(?:[^\n]*)\n(.*?)```", markdown, re.DOTALL)
    ]
    blocks.extend(_collect_string_values_by_key(payload, {"code", "code_text", "program"}))
    return tuple(dict.fromkeys(block for block in blocks if block))


def _extract_docling_figure_captions(
    assets: tuple[DoclingAsset, ...], payload: Any
) -> tuple[str, ...]:
    captions = [
        asset.caption.strip()
        for asset in assets
        if asset.caption and asset.caption.strip()
    ]
    captions.extend(_collect_string_values_by_key(payload, {"caption", "caption_text"}))
    return tuple(dict.fromkeys(caption for caption in captions if caption))


def _extract_glossary_index_hints(
    sections: tuple[DoclingSection, ...], payload: Any
) -> tuple[str, ...]:
    hints = [section.title for section in sections if _is_glossary_or_index_title(section.title)]
    hints.extend(_collect_string_values_by_key(payload, {"glossary", "index"}))
    return tuple(dict.fromkeys(hint for hint in hints if hint))


def _collect_string_values_by_key(payload: Any, wanted: set[str]) -> list[str]:
    values: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key).strip().lower() in wanted:
                if isinstance(value, str):
                    values.append(value.strip())
                elif isinstance(value, list):
                    values.extend(str(item).strip() for item in value if str(item).strip())
            values.extend(_collect_string_values_by_key(value, wanted))
    elif isinstance(payload, list):
        for item in payload:
            values.extend(_collect_string_values_by_key(item, wanted))
    return values


def _is_glossary_or_index_title(title: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    return normalized in {"glossary", "index", "glossary and index", "index and glossary"}


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
