from __future__ import annotations

import hashlib
import json
import re
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
    archived_previous = None
    if out_dir.exists():
        if not force:
            raise FileExistsError(f"Ingestion directory exists: {out_dir}. Re-run with --force.")
        archived_previous = archive_existing_slug(ingestion_root=ingestion_root, slug_dir=out_dir)

    conversion = convert_pdf_with_docling(source)
    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "attachments").mkdir(exist_ok=True)
    (out_dir / "tables").mkdir(exist_ok=True)
    (out_dir / "index.md").write_text(
        f"---\nstatus: ingested\norigin: {slug}\n---\n\n# {source.stem}\n", encoding="utf-8"
    )
    (out_dir / "00_metadata.md").write_text(
        f"---\nstatus: ingested\nsource_pdf: {source.as_posix()}\n---\n", encoding="utf-8"
    )
    (out_dir / "01_full-document.md").write_text(
        conversion.markdown.strip() + "\n", encoding="utf-8"
    )
    for idx, asset in enumerate(conversion.assets, start=1):
        (out_dir / "attachments" / f"fig_{idx:04d}_{Path(asset.relative_path).name}").write_bytes(
            asset.content
        )
    manifest = {
        "source_pdf": source.as_posix(),
        "source_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
        "ingest_time": datetime.now(timezone.utc).isoformat(),
        "ingest_tool": "docling",
        "document_type": "pdf",
        "origin": slug,
        "outputs": {
            "index": "index.md",
            "metadata": "00_metadata.md",
            "section_notes": ["01_full-document.md"],
            "attachments_count": len(conversion.assets),
            "tables_count": 0 if conversion.tables_json is None else len(conversion.tables_json),
        },
    }
    manifest_path = out_dir / "_ingest_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return IngestResult(
        slug=slug,
        output_dir=out_dir,
        archived_previous=archived_previous,
        manifest_path=manifest_path,
    )
