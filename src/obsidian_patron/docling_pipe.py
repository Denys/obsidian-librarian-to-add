from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from obsidian_librarian.pdf_docling import (
    DoclingConversionResult,
    DoclingSection,
    convert_pdf_with_docling,
)
from obsidian_patron.safety import archive_existing_slug, ensure_under


@dataclass(frozen=True)
class IngestResult:
    slug: str
    output_dir: Path
    archived_previous: Path | None
    manifest_path: Path


def slugify(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return cleaned or "document"


def ingest_pdf_to_ingestion(
    pdf_path: str | Path, vault_root: str | Path, *, force: bool = False
) -> IngestResult:
    source = Path(pdf_path).expanduser().resolve(strict=False)
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"PDF source not found: {source}")

    vault = Path(vault_root).expanduser().resolve(strict=False)
    ingestion_root = (vault / "91_Ingestion").resolve(strict=False)
    ingestion_root.mkdir(parents=True, exist_ok=True)
    ensure_under(vault, ingestion_root)

    slug = slugify(source.stem)
    out_dir = ensure_under(ingestion_root, ingestion_root / slug)
    out_dir_exists = out_dir.exists()
    if out_dir_exists and not force:
        raise FileExistsError(f"Ingestion directory exists: {out_dir}. Re-run with --force.")

    run_id = str(uuid.uuid4())
    conversion = convert_pdf_with_docling(source)

    temp_dir = ensure_under(ingestion_root, ingestion_root / f".{slug}.tmp-{run_id}")
    temp_dir.mkdir(parents=True, exist_ok=False)
    (temp_dir / "attachments").mkdir(exist_ok=True)
    (temp_dir / "tables").mkdir(exist_ok=True)

    sections = _section_notes(conversion)
    section_files = _write_section_notes(temp_dir, sections, source, slug, run_id)
    _write_index_note(temp_dir, source, slug, run_id, section_files)
    _write_metadata_note(temp_dir, source, slug, run_id, conversion.metadata or {})
    _write_table_sidecars(temp_dir, conversion)
    attachment_files = _write_assets(temp_dir, conversion)

    manifest = {
        "source_pdf": source.as_posix(),
        "source_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
        "ingest_time": datetime.now(timezone.utc).isoformat(),
        "ingest_tool": "docling",
        "document_type": "pdf",
        "origin": slug,
        "ingest_run_id": run_id,
        "outputs": {
            "index": "index.md",
            "metadata": "00_metadata.md",
            "section_notes": [filename for filename, _title in section_files],
            "attachments": attachment_files,
            "attachments_count": len(conversion.assets),
            "tables_count": _count_conversion_tables(conversion),
            "code_blocks_count": len(conversion.code_blocks),
            "figure_captions_count": len(conversion.figure_captions),
            "glossary_index_hints": list(conversion.glossary_index_hints),
        },
    }
    temp_manifest = temp_dir / "_ingest_manifest.json"
    temp_manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    archived_previous = None
    if out_dir_exists:
        archived_previous = archive_existing_slug(ingestion_root=ingestion_root, slug_dir=out_dir)
    temp_dir.replace(out_dir)
    return IngestResult(
        slug=slug,
        output_dir=out_dir,
        archived_previous=archived_previous,
        manifest_path=out_dir / "_ingest_manifest.json",
    )


def _section_notes(conversion: DoclingConversionResult) -> tuple[DoclingSection, ...]:
    sections = conversion.sections or _split_markdown_top_level_sections(conversion.markdown)
    if not sections:
        return (DoclingSection(title="Document", markdown=conversion.markdown.strip() + "\n"),)
    return sections


def _write_section_notes(
    temp_dir: Path,
    sections: tuple[DoclingSection, ...],
    source: Path,
    origin: str,
    run_id: str,
) -> list[tuple[str, str]]:
    used_slugs: set[str] = set()
    written: list[tuple[str, str]] = []
    for index, section in enumerate(sections, start=1):
        section_slug = _unique_slug(slugify(section.title), used_slugs)
        filename = f"{index:02d}_{section_slug}.md"
        section_kind = section.kind or (
            "glossary-index" if _is_glossary_or_index(section.title) else "section"
        )
        frontmatter = {
            "status": "ingested",
            "origin": origin,
            "ingest_run_id": run_id,
            "source_pdf": source.as_posix(),
            "section": section_slug,
            "section_title": section.title,
            "section_kind": section_kind,
        }
        body = section.markdown.strip() or f"# {section.title}"
        (temp_dir / filename).write_text(
            _frontmatter(frontmatter) + "\n" + body + "\n",
            encoding="utf-8",
        )
        written.append((filename, section.title))
    return written


def _write_index_note(
    temp_dir: Path,
    source: Path,
    origin: str,
    run_id: str,
    section_files: list[tuple[str, str]],
) -> None:
    lines = [
        _frontmatter({"status": "ingested", "origin": origin, "ingest_run_id": run_id}),
        "",
        f"# {source.stem}",
        "",
        f"- Source path: `{source.as_posix()}`",
        "- Ingest status: ingested",
        f"- Ingest run ID: `{run_id}`",
        "",
        "## Table of contents",
        "",
    ]
    for filename, title in section_files:
        lines.append(f"- [[{Path(filename).stem}|{title}]]")
    lines.append("")
    (temp_dir / "index.md").write_text("\n".join(lines), encoding="utf-8")


def _write_metadata_note(
    temp_dir: Path,
    source: Path,
    origin: str,
    run_id: str,
    metadata: dict[str, Any],
) -> None:
    frontmatter = {
        "status": "ingested",
        "origin": origin,
        "ingest_run_id": run_id,
        "source_pdf": source.as_posix(),
    }
    frontmatter.update(_available_metadata_fields(metadata))
    lines = [_frontmatter(frontmatter), "", "# Metadata", ""]
    for key, value in _available_metadata_fields(metadata).items():
        lines.append(f"- {key}: {_metadata_inline(value)}")
    lines.append("")
    (temp_dir / "00_metadata.md").write_text("\n".join(lines), encoding="utf-8")


def _write_table_sidecars(temp_dir: Path, conversion: DoclingConversionResult) -> None:
    if conversion.tables_json:
        (temp_dir / "tables" / "tables.json").write_text(conversion.tables_json, encoding="utf-8")


def _write_assets(temp_dir: Path, conversion: DoclingConversionResult) -> list[str]:
    written: list[str] = []
    for index, asset in enumerate(conversion.assets, start=1):
        target_name = _figure_filename(index, asset.relative_path, asset.caption)
        target = temp_dir / "attachments" / target_name
        target.write_bytes(asset.content)
        written.append(f"attachments/{target_name}")
    return written


def _figure_filename(index: int, relative_path: Path, caption: str | None) -> str:
    suffix = Path(relative_path).suffix.lower() or ".png"
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
        suffix = ".png"
    stem_source = caption if caption and caption.strip() else Path(relative_path).stem
    return f"fig_{index:04d}_{slugify(stem_source)}{suffix}"


def _available_metadata_fields(metadata: dict[str, Any]) -> dict[str, Any]:
    wanted = (
        "title",
        "authors",
        "author",
        "year",
        "publication_year",
        "isbn",
        "subject",
        "keywords",
    )
    return {
        key: metadata[key]
        for key in wanted
        if key in metadata and metadata[key] not in (None, "")
    }


def _frontmatter(values: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in values.items():
        lines.append(f"{key}: {_yaml_value(value)}")
    lines.append("---")
    return "\n".join(lines)


def _yaml_value(value: Any) -> str:
    if isinstance(value, list | tuple):
        return "[" + ", ".join(_yaml_scalar(item) for item in value) + "]"
    return _yaml_scalar(value)


def _yaml_scalar(value: Any) -> str:
    text = str(value)
    if re.fullmatch(r"[A-Za-z0-9_./:+-]+", text):
        return text
    return json.dumps(text)


def _metadata_inline(value: Any) -> str:
    if isinstance(value, list | tuple):
        return ", ".join(str(item) for item in value)
    return str(value)


def _unique_slug(candidate: str, used: set[str]) -> str:
    base = candidate or "section"
    current = base
    suffix = 2
    while current in used:
        current = f"{base}-{suffix}"
        suffix += 1
    used.add(current)
    return current


def _split_markdown_top_level_sections(markdown: str) -> tuple[DoclingSection, ...]:
    lines = markdown.strip().splitlines()
    sections: list[DoclingSection] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in lines:
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            if current_title is not None:
                sections.append(
                    DoclingSection(
                        title=current_title,
                        markdown="\n".join(current_lines).strip() + "\n",
                    )
                )
            current_title = match.group(1).strip()
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


def _is_glossary_or_index(title: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    return normalized in {"glossary", "index", "glossary and index", "index and glossary"}


def _count_conversion_tables(conversion: DoclingConversionResult) -> int:
    if conversion.tables:
        return len(conversion.tables)
    return _count_tables(conversion.tables_json)


def _count_tables(tables_json: str | None) -> int:
    if not tables_json:
        return 0
    try:
        payload = json.loads(tables_json)
    except json.JSONDecodeError:
        return 0
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        tables = payload.get("tables")
        if isinstance(tables, list):
            return len(tables)
        if tables:
            return 1
    return 0
