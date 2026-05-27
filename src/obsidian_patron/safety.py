from __future__ import annotations

import shutil
from pathlib import Path


def ensure_under(root: Path, target: Path) -> Path:
    root_resolved = root.expanduser().resolve(strict=False)
    target_resolved = target.expanduser().resolve(strict=False)
    if not target_resolved.is_relative_to(root_resolved):
        raise ValueError(f"Refusing write outside allowed root: {target_resolved}")
    return target_resolved


def archive_existing_slug(*, ingestion_root: Path, slug_dir: Path) -> Path:
    archive_root = ingestion_root / "_archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    archived = archive_root / slug_dir.name
    suffix = 2
    while archived.exists():
        archived = archive_root / f"{slug_dir.name}-{suffix}"
        suffix += 1
    shutil.move(str(slug_dir), str(archived))
    return archived
