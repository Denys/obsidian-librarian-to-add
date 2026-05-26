"""Optional Docling PDF conversion adapter for Phase 11.2+11.4."""

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
class DoclingAsset:
    """One staged binary/text asset exported by a PDF converter."""

    relative_path: Path
    content: bytes


@dataclass(frozen=True)
class DoclingConversionResult:
    """Docling conversion output needed by the staging writer."""

    markdown: str
    structured_json: str
    engine_version: str
    tables_json: str | None = None
    assets: tuple[DoclingAsset, ...] = ()


def convert_pdf_with_docling(path: str | Path) -> DoclingConversionResult:
    """Convert a PDF with Docling and return Markdown plus structured sidecars."""
    pdf_path = Path(path).expanduser().resolve(strict=False)
    converter_cls = _load_docling_converter()

    try:
        converter = converter_cls()
        result = converter.convert(pdf_path)
        document = result.document
        markdown = document.export_to_markdown()
        structured_payload = _export_docling_payload(document)
        structured = _json_dumps(structured_payload)
        tables_json = _export_docling_tables_json(structured_payload)
    except Exception as exc:
        raise PdfConversionError(f"Docling conversion failed for {pdf_path}: {exc}") from exc

    if not markdown.strip():
        raise PdfConversionError(f"Docling produced empty Markdown for {pdf_path}")

    return DoclingConversionResult(
        markdown=markdown,
        structured_json=structured,
        engine_version=_docling_version(),
        tables_json=tables_json,
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
