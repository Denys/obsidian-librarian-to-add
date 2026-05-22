"""Shared data models for deterministic ingest."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SourceDocument:
    """Parsed source document from an inbox."""

    path: Path
    relative_path: Path
    source_kind: str
    title: str
    content: str
    action_items: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkippedFile:
    """File skipped during ingest."""

    path: Path
    reason: str


@dataclass(frozen=True)
class GeneratedNote:
    """Generated staged note metadata."""

    source_path: Path
    staged_path: Path
    note_type: str


@dataclass(frozen=True)
class PdfWarning:
    """Structured warning emitted during deterministic PDF classification."""

    code: str
    message: str


@dataclass(frozen=True)
class PdfTextDensity:
    """Conservative text-density signal from a stdlib-only PDF probe."""

    total_chars: int
    chars_per_page_min: int
    chars_per_page_median: int
    empty_pages: int


@dataclass(frozen=True)
class PdfExtraction:
    """Metadata about how PDF information was produced."""

    method: str
    engine_version: str | None = None
    ocr_enabled: bool = False
    warnings: tuple[PdfWarning, ...] = ()


@dataclass(frozen=True)
class PdfOutputs:
    """Generated PDF artifact references recorded in a manifest."""

    root: str | None = None
    markdown_note: str | None = None
    json_sidecar: str | None = None
    table_sidecars: tuple[str, ...] = ()
    asset_dir: str | None = None


@dataclass(frozen=True)
class PdfPageRange:
    """Page range to output-anchor mapping for later provenance validation."""

    page_start: int
    page_end: int
    output_anchor: str


@dataclass(frozen=True)
class PdfProvenance:
    """PDF page-level provenance references."""

    page_ranges: tuple[PdfPageRange, ...] = ()


@dataclass(frozen=True)
class PdfManifest:
    """Deterministic metadata about one PDF source and planned/generated artifacts."""

    schema_version: int
    source_path: str
    source_hash: str
    source_kind: str
    status: str
    page_count: int
    classification: str
    text_density: PdfTextDensity
    extraction: PdfExtraction
    outputs: PdfOutputs = field(default_factory=PdfOutputs)
    provenance: PdfProvenance = field(default_factory=PdfProvenance)


@dataclass
class IngestRunResult:
    """Result of one inbox ingest run."""

    inbox_root: Path
    vault_root: Path
    mode: str
    processed: list[SourceDocument] = field(default_factory=list)
    skipped: list[SkippedFile] = field(default_factory=list)
    generated: list[GeneratedNote] = field(default_factory=list)
    pdf_manifests: list[PdfManifest] = field(default_factory=list)
    pdf_manifest_paths: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    report_path: Path | None = None
