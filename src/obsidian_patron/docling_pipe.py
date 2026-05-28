from __future__ import annotations

import hashlib
import json
import re
import shutil
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
from obsidian_patron.safety import (
    archive_existing_slug,
    ensure_under,
    validate_ingestion_write_contract,
)


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
    try:
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

        validate_ingestion_write_contract(
            temp_dir,
            origin=slug,
            ingest_run_id=run_id,
            source_pdf=source,
            vault_root=vault,
        )

        archived_previous = None
        if out_dir_exists:
            archived_previous = archive_existing_slug(
                ingestion_root=ingestion_root, slug_dir=out_dir
            )
        temp_dir.replace(out_dir)
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise
    return IngestResult(
        slug=slug,
        output_dir=out_dir,
        archived_previous=archived_previous,
        manifest_path=out_dir / "_ingest_manifest.json",
    )


def _section_notes(conversion: DoclingConversionResult) -> tuple[DoclingSection, ...]:
    if conversion.sections:
        return conversion.sections
    markdown = conversion.markdown.strip()
    return (
        DoclingSection(
            title="Full Document",
            markdown=markdown,
            heading_path=_first_heading_path(markdown) or "full-document",
        ),
    )


def _first_heading_path(markdown: str) -> str | None:
    match = re.search(r"^#{1,6}\s+(.+?)\s*$", markdown, re.MULTILINE)
    if not match:
        return None
    return slugify(match.group(1))


def _write_section_notes(
    temp_dir: Path,
    sections: tuple[DoclingSection, ...],
    source: Path,
    slug: str,
    run_id: str,
) -> list[tuple[str, str]]:
    written: list[tuple[str, str]] = []
    for index, section in enumerate(sections, start=1):
        filename = f"{index:02d}_{slugify(section.title)}.md"
        frontmatter = [
            "---",
            "status: ingested",
            f"origin: {slug}",
            f"ingest_run_id: {run_id}",
            f"source_pdf: {source.as_posix()}",
            f"source_section: {section.heading_path}",
        ]
        if section.kind:
            frontmatter.append(f"section_kind: {section.kind}")
        frontmatter.append("---")
        body = section.markdown.strip()
        (temp_dir / filename).write_text(
            "\n".join(frontmatter) + f"\n\n{body}\n",
            encoding="utf-8",
        )
        written.append((filename, section.title))
    return written


def _write_index_note(
    temp_dir: Path,
    source: Path,
    slug: str,
    run_id: str,
    section_files: list[tuple[str, str]],
) -> None:
    lines = [
        "---",
        "status: ingested",
        f"origin: {slug}",
        f"ingest_run_id: {run_id}",
        f"source_pdf: {source.as_posix()}",
        "---",
        "",
        f"# {source.stem}",
        "",
        "Ingest status: ingested",
        "",
        "## Sections",
        "",
    ]
    for filename, title in section_files:
        lines.append(f"- [[{Path(filename).stem}|{title}]]")
    (temp_dir / "index.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_metadata_note(
    temp_dir: Path,
    source: Path,
    slug: str,
    run_id: str,
    metadata: dict[str, Any],
) -> None:
    lines = [
        "---",
        "status: ingested",
        f"origin: {slug}",
        f"ingest_run_id: {run_id}",
        f"source_pdf: {source.as_posix()}",
    ]
    for key in sorted(metadata):
        lines.append(f"{key}: {_yaml_scalar(metadata[key])}")
    lines.extend(["---", ""])
    (temp_dir / "00_metadata.md").write_text("\n".join(lines), encoding="utf-8")


def _write_table_sidecars(temp_dir: Path, conversion: DoclingConversionResult) -> None:
    if conversion.tables_json:
        (temp_dir / "tables" / "tables.json").write_text(conversion.tables_json, encoding="utf-8")


def _write_assets(temp_dir: Path, conversion: DoclingConversionResult) -> list[str]:
    attachment_files: list[str] = []
    for idx, asset in enumerate(conversion.assets, start=1):
        target_name = _asset_target_name(asset.relative_path, asset.caption, idx)
        relative = f"attachments/{target_name}"
        (temp_dir / relative).write_bytes(asset.content)
        attachment_files.append(relative)
    return attachment_files


def _asset_target_name(relative_path: Path, caption: str | None, index: int) -> str:
    path = Path(relative_path)
    suffix = path.suffix or ".bin"
    basename = slugify(caption or path.stem)
    return f"fig_{index:04d}_{basename}{suffix}"


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(str(item) for item in value) + "]"
    return str(value)


def _count_conversion_tables(conversion: DoclingConversionResult) -> int:
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
