from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from obsidian_librarian.pdf_docling import convert_pdf_with_docling
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

    index_text = (
        "---\n"
        "status: ingested\n"
        f"origin: {slug}\n"
        f"ingest_run_id: {run_id}\n"
        "---\n\n"
        f"# {source.stem}\n"
    )
    (temp_dir / "index.md").write_text(index_text, encoding="utf-8")

    metadata_text = (
        "---\n"
        "status: ingested\n"
        f"origin: {slug}\n"
        f"ingest_run_id: {run_id}\n"
        f"source_pdf: {source.as_posix()}\n"
        "---\n"
    )
    (temp_dir / "00_metadata.md").write_text(metadata_text, encoding="utf-8")

    (temp_dir / "01_full-document.md").write_text(
        conversion.markdown.strip() + "\n",
        encoding="utf-8",
    )
    for idx, asset in enumerate(conversion.assets, start=1):
        target = temp_dir / "attachments" / f"fig_{idx:04d}_{Path(asset.relative_path).name}"
        target.write_bytes(asset.content)

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
            "section_notes": ["01_full-document.md"],
            "attachments_count": len(conversion.assets),
            "tables_count": 0 if conversion.tables_json is None else len(conversion.tables_json),
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
