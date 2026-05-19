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


@dataclass
class IngestRunResult:
    """Result of one inbox ingest run."""

    inbox_root: Path
    vault_root: Path
    mode: str
    processed: list[SourceDocument] = field(default_factory=list)
    skipped: list[SkippedFile] = field(default_factory=list)
    generated: list[GeneratedNote] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    report_path: Path | None = None
