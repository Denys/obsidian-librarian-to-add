"""Deterministic stdlib-only PDF classifier for Phase 11.1.

This module intentionally does not convert PDF content to Markdown. It only creates a
conservative manifest that can be reviewed before any Docling/OCR phase is enabled.
"""

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
    """Return PDF files under an inbox directory in deterministic order."""
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
    """Classify one PDF source and return a deterministic manifest."""
    pdf_path = Path(path).expanduser().resolve(strict=False)
    source_path = _manifest_source_path(pdf_path, source_root)

    try:
        data = pdf_path.read_bytes()
    except OSError as exc:
        return _failed_manifest(
            source_path=source_path,
            source_hash="",
            classification="malformed_pdf",
            warning=PdfWarning("read_failed", f"Could not read PDF source: {exc}"),
        )

    source_hash = hashlib.sha256(data).hexdigest()
    warnings: list[PdfWarning] = []

    if not data.startswith(b"%PDF-"):
        return _failed_manifest(
            source_path=source_path,
            source_hash=source_hash,
            classification="malformed_pdf",
            warning=PdfWarning("invalid_header", "File does not start with a PDF header."),
        )

    page_count = len(_PAGE_RE.findall(data))
    if b"/Encrypt" in data:
        warnings.append(PdfWarning("encrypted_pdf", "PDF appears encrypted or locked."))
        return _manifest(
            source_path=source_path,
            source_hash=source_hash,
            status="skipped",
            page_count=page_count,
            classification="encrypted_pdf",
            text_density=_zero_density(page_count),
            warnings=tuple(warnings),
        )

    if page_count <= 0:
        warnings.append(PdfWarning("missing_pages", "No PDF page objects were detected."))
        return _manifest(
            source_path=source_path,
            source_hash=source_hash,
            status="failed",
            page_count=0,
            classification="malformed_pdf",
            text_density=_zero_density(0),
            warnings=tuple(warnings),
        )

    total_chars = _estimate_text_chars(data)
    density = _density(total_chars, page_count)
    image_count = len(_IMAGE_RE.findall(data))

    if total_chars == 0 and image_count > 0:
        warnings.append(
            PdfWarning(
                "ocr_needed",
                "PDF has image objects but no detectable text; "
                "OCR is deferred and must be explicit.",
            )
        )
        classification = "scanned_pdf"
        status = "skipped"
    elif total_chars < page_count * _LOW_TEXT_CHARS_PER_PAGE:
        warnings.append(
            PdfWarning(
                "low_text_density",
                "PDF has low detectable text density; conversion should be reviewed before trust.",
            )
        )
        classification = "unknown" if image_count == 0 else "mixed_pdf"
        status = "needs_review"
    elif image_count > 0:
        warnings.append(
            PdfWarning(
                "mixed_content",
                "PDF contains detectable text and image objects; tables/figures remain deferred.",
            )
        )
        classification = "mixed_pdf"
        status = "needs_review"
    else:
        classification = "digital_pdf"
        status = "staged"

    return _manifest(
        source_path=source_path,
        source_hash=source_hash,
        status=status,
        page_count=page_count,
        classification=classification,
        text_density=density,
        warnings=tuple(warnings),
    )


def manifest_to_dict(manifest: PdfManifest) -> dict[str, object]:
    """Convert a PDF manifest dataclass into JSON-compatible data."""
    return asdict(manifest)


def render_pdf_manifest_json(manifest: PdfManifest) -> str:
    """Render a PDF manifest as stable, human-reviewable JSON."""
    return json.dumps(manifest_to_dict(manifest), indent=2, sort_keys=True) + "\n"


def staged_pdf_root_path(manifest: PdfManifest) -> Path:
    """Return the relative staged directory path for all artifacts from one PDF."""
    source = Path(manifest.source_path)
    parent_parts = [sanitize_path_part(part) for part in source.parent.parts]
    stem = sanitize_path_part(source.stem)
    return Path("pdf", *parent_parts, stem)


def staged_pdf_manifest_path(manifest: PdfManifest) -> Path:
    """Return the relative staged path for a PDF manifest sidecar."""
    return staged_pdf_root_path(manifest) / "manifest.json"


def staged_pdf_markdown_path(manifest: PdfManifest) -> Path:
    """Return the relative staged path for Docling Markdown output."""
    return staged_pdf_root_path(manifest) / "source.md"


def staged_pdf_structured_json_path(manifest: PdfManifest) -> Path:
    """Return the relative staged path for Docling structured JSON output."""
    return staged_pdf_root_path(manifest) / "docling.json"


def _manifest_source_path(pdf_path: Path, source_root: str | Path | None) -> str:
    if source_root is None:
        return pdf_path.as_posix()

    root = Path(source_root).expanduser().resolve(strict=False)
    try:
        return pdf_path.relative_to(root).as_posix()
    except ValueError:
        return pdf_path.as_posix()


def _estimate_text_chars(data: bytes) -> int:
    literal_matches = _LITERAL_TEXT_RE.findall(data)
    if not literal_matches:
        literal_matches = _ANY_LITERAL_RE.findall(data)

    total = 0
    for match in literal_matches:
        total += _count_printable_pdf_literal(match)
    return total


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
    return PdfTextDensity(
        total_chars=total_chars,
        chars_per_page_min=per_page,
        chars_per_page_median=per_page,
        empty_pages=empty_pages,
    )


def _zero_density(page_count: int) -> PdfTextDensity:
    return PdfTextDensity(
        total_chars=0,
        chars_per_page_min=0,
        chars_per_page_median=0,
        empty_pages=max(page_count, 0),
    )


def _failed_manifest(
    *,
    source_path: str,
    source_hash: str,
    classification: str,
    warning: PdfWarning,
) -> PdfManifest:
    return _manifest(
        source_path=source_path,
        source_hash=source_hash,
        status="failed",
        page_count=0,
        classification=classification,
        text_density=_zero_density(0),
        warnings=(warning,),
    )


def _manifest(
    *,
    source_path: str,
    source_hash: str,
    status: str,
    page_count: int,
    classification: str,
    text_density: PdfTextDensity,
    warnings: tuple[PdfWarning, ...],
) -> PdfManifest:
    manifest = PdfManifest(
        schema_version=PDF_MANIFEST_SCHEMA_VERSION,
        source_path=source_path,
        source_hash=source_hash,
        source_kind="pdf",
        status=status,
        page_count=page_count,
        classification=classification,
        text_density=text_density,
        extraction=PdfExtraction(
            method="classifier_probe",
            engine_version=PDF_PROBE_VERSION,
            ocr_enabled=False,
            warnings=warnings,
        ),
        outputs=PdfOutputs(),
        provenance=PdfProvenance(),
    )
    return PdfManifest(
        **{
            **manifest_to_dict(manifest),
            "outputs": PdfOutputs(root=staged_pdf_root_path(manifest).as_posix()),
        }
    )