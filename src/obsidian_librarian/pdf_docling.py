"""Optional Docling PDF conversion adapter for Phase 11.2."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import import_module, metadata
from pathlib import Path
from typing import Any


class PdfConversionError(RuntimeError):
    """Raised when PDF conversion fails safely."""


class PdfDependencyError(PdfConversionError):
    """Raised when the optional Docling dependency is missing."""


@dataclass(frozen=True)
class DoclingConversionResult:
    """Docling conversion output needed by the staging writer."""

    markdown: str
    structured_json: str
    engine_version: str


def convert_pdf_with_docling(path: str | Path) -> DoclingConversionResult:
    """Convert a PDF with Docling and return Markdown plus structured JSON."""
    pdf_path = Path(path).expanduser().resolve(strict=False)
    converter_cls = _load_docling_converter()

    try:
        converter = converter_cls()
        result = converter.convert(pdf_path)
        document = result.document
        markdown = document.export_to_markdown()
        structured = _export_docling_json(document)
    except Exception as exc:
        raise PdfConversionError(f"Docling conversion failed for {pdf_path}: {exc}") from exc

    if not markdown.strip():
        raise PdfConversionError(f"Docling produced empty Markdown for {pdf_path}")

    return DoclingConversionResult(
        markdown=markdown,
        structured_json=structured,
        engine_version=_docling_version(),
    )


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


def _docling_version() -> str:
    try:
        return metadata.version("docling")
    except metadata.PackageNotFoundError:
        return "unknown"


def _export_docling_json(document: Any) -> str:
    for method_name in ("export_to_dict", "model_dump"):
        method = getattr(document, method_name, None)
        if callable(method):
            payload = method()
            return json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"

    return json.dumps({"repr": repr(document)}, indent=2, sort_keys=True) + "\n"
