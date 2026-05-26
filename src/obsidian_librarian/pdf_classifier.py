"""Deterministic stdlib-only PDF classifier."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from pathlib import Path

from obsidian_librarian.models import (
    PdfExtraction,
    PdfManifest,
    PdfOutputs,
    PdfProvenance,
    PdfTextDensity,
    PdfWarning,
)
from obsidian_librarian.renderers import sanitize_path_part

PDF_MANIFEST_SCHEMA_VERSION = 1
PDF_PROBE_VERSION = "stdlib-pdf-probe-0.1"
_LOW_TEXT_CHARS_PER_PAGE = 20
_PAGE_RE = re.compile(rb"/Type\s*/Page\b")
_IMAGE_RE = re.compile(rb"/Subtype\s*/Image\b")
_LITERAL_TEXT_RE = re.compile(rb"\((?:\\.|[^\\)]){2,}\)\s*(?:Tj|TJ|'|\")")
_ANY_LITERAL_RE = re.compile(rb"\((?:\\.|[^\\)]){2,}\)")


def discover_pdf_sources(inbox_root: str | Path) -> list[Path]:
    root = Path(inbox_root).expanduser().resolve(strict=False)
    if not root.exists():
        raise FileNotFoundError(f"Inbox directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Inbox path is not a directory: {root}")
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() == ".pdf"
    )


def classify_pdf_source(path: str | Path, *, source_root: str | Path | None = None) -> PdfManifest:
    pdf_path = Path(path).expanduser().resolve(strict=False)
    source_path = _manifest_source_path(pdf_path, source_root)
    try:
        data = pdf_path.read_bytes()
    except OSError as exc:
        return _failed_manifest(source_path, "", "malformed_pdf", "read_failed", str(exc))

    source_hash = hashlib.sha256(data).hexdigest()
    if not data.startswith(b"%PDF-"):
        return _failed_manifest(
            source_path,
            source_hash,
            "malformed_pdf",
            "invalid_header",
            "File does not start with a PDF header.",
        )

    page_count = len(_PAGE_RE.findall(data))
    if b"/Encrypt" in data:
        return _manifest(
            source_path,
            source_hash,
            "skipped",
            page_count,
            "encrypted_pdf",
            _zero_density(page_count),
            (PdfWarning("encrypted_pdf", "PDF appears encrypted or locked."),),
        )
    if page_count <= 0:
        return _manifest(
            source_path,
            source_hash,
            "failed",
            0,
            "malformed_pdf",
            _zero_density(0),
            (PdfWarning("missing_pages", "No PDF page objects were detected."),),
        )

    total_chars = _estimate_text_chars(data)
    density = _density(total_chars, page_count)
    image_count = len(_IMAGE_RE.findall(data))

    if total_chars == 0 and image_count > 0:
        return _manifest(
            source_path,
            source_hash,
            "skipped",
            page_count,
            "scanned_pdf",
            density,
            (PdfWarning("ocr_needed", "PDF has no detectable text; OCR is deferred."),),
        )
    if total_chars < page_count * _LOW_TEXT_CHARS_PER_PAGE:
        classification = "unknown" if image_count == 0 else "mixed_pdf"
        return _manifest(
            source_path,
            source_hash,
            "needs_review",
            page_count,
            classification,
            density,
            (PdfWarning("low_text_density", "PDF has low detectable text density."),),
        )
    if image_count > 0:
        return _manifest(
            source_path,
            source_hash,
            "needs_review",
            page_count,
            "mixed_pdf",
            density,
            (PdfWarning("mixed_content", "PDF contains detectable text and images."),),
        )
    return _manifest(
        source_path,
        source_hash,
        "staged",
        page_count,
        "digital_pdf",
        density,
        (),
    )


def manifest_to_dict(manifest: PdfManifest) -> dict[str, object]:
    return asdict(manifest)


def render_pdf_manifest_json(manifest: PdfManifest) -> str:
    return json.dumps(manifest_to_dict(manifest), indent=2, sort_keys=True) + "\n"


def staged_pdf_root_path(manifest: PdfManifest) -> Path:
    return _staged_pdf_root_for_source(manifest.source_path)


def staged_pdf_manifest_path(manifest: PdfManifest) -> Path:
    return staged_pdf_root_path(manifest) / "manifest.json"


def staged_pdf_markdown_path(manifest: PdfManifest) -> Path:
    return staged_pdf_root_path(manifest) / "source.md"


def staged_pdf_structured_json_path(manifest: PdfManifest) -> Path:
    return staged_pdf_root_path(manifest) / "docling.json"


def staged_pdf_tables_json_path(manifest: PdfManifest) -> Path:
    return staged_pdf_root_path(manifest) / "tables.json"


def staged_pdf_assets_dir_path(manifest: PdfManifest) -> Path:
    return staged_pdf_root_path(manifest) / "assets"


def _staged_pdf_root_for_source(source_path: str) -> Path:
    source = Path(source_path)
    parent_parts = [sanitize_path_part(part) for part in source.parent.parts]
    return Path("pdf", *parent_parts, sanitize_path_part(source.stem))


def _manifest_source_path(pdf_path: Path, source_root: str | Path | None) -> str:
    if source_root is None:
        return pdf_path.as_posix()
    root = Path(source_root).expanduser().resolve(strict=False)
    try:
        return pdf_path.relative_to(root).as_posix()
    except ValueError:
        return pdf_path.as_posix()


def _estimate_text_chars(data: bytes) -> int:
    matches = _LITERAL_TEXT_RE.findall(data) or _ANY_LITERAL_RE.findall(data)
    return sum(_count_printable_pdf_literal(match) for match in matches)


def _count_printable_pdf_literal(match: bytes) -> int:
    start = match.find(b"(")
    end = match.rfind(b")")
    if start < 0 or end <= start:
        return 0
    literal = match[start + 1 : end].decode("latin-1", errors="ignore")
    return sum(1 for char in literal if char.isprintable() and not char.isspace())


def _density(total_chars: int, page_count: int) -> PdfTextDensity:
    if page_count <= 0:
        return _zero_density(0)
    per_page = total_chars // page_count
    empty_pages = page_count if total_chars == 0 else 0
    return PdfTextDensity(total_chars, per_page, per_page, empty_pages)


def _zero_density(page_count: int) -> PdfTextDensity:
    return PdfTextDensity(0, 0, 0, max(page_count, 0))


def _failed_manifest(
    source_path: str,
    source_hash: str,
    classification: str,
    code: str,
    message: str,
) -> PdfManifest:
    return _manifest(
        source_path,
        source_hash,
        "failed",
        0,
        classification,
        _zero_density(0),
        (PdfWarning(code, message),),
    )


def _manifest(
    source_path: str,
    source_hash: str,
    status: str,
    page_count: int,
    classification: str,
    text_density: PdfTextDensity,
    warnings: tuple[PdfWarning, ...],
) -> PdfManifest:
    return PdfManifest(
        schema_version=PDF_MANIFEST_SCHEMA_VERSION,
        source_path=source_path,
        source_hash=source_hash,
        source_kind="pdf",
        status=status,
        page_count=page_count,
        classification=classification,
        text_density=text_density,
        extraction=PdfExtraction("classifier_probe", PDF_PROBE_VERSION, False, warnings),
        outputs=PdfOutputs(root=_staged_pdf_root_for_source(source_path).as_posix()),
        provenance=PdfProvenance(),
    )