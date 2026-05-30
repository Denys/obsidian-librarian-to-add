from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path


class IngestionContractError(ValueError):
    """Raised when generated 91_Ingestion files violate the write contract."""


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


def validate_ingestion_write_contract(
    ingestion_dir: Path,
    *,
    origin: str,
    ingest_run_id: str,
    source_pdf: Path | str,
    vault_root: Path | str | None = None,
) -> None:
    """Validate freshly generated notes before publishing them under 91_Ingestion.

    The explicit linking phase is responsible for adding trusted-note wikilinks later, so
    fresh ingestion output may not contain wikilinks that already target trusted vault notes.
    """

    if not ingestion_dir.exists() or not ingestion_dir.is_dir():
        raise IngestionContractError(f"Ingestion output directory not found: {ingestion_dir}")

    _validate_uuid(ingest_run_id)
    source_pdf_text = _normalize_source_pdf(source_pdf)
    trusted_targets = _trusted_wikilink_targets(vault_root) if vault_root is not None else None
    markdown_paths = _normal_markdown_files(ingestion_dir)
    if not markdown_paths:
        raise IngestionContractError(f"No Markdown notes generated in: {ingestion_dir}")
    # Same-folder links (e.g. the index.md table of contents) target freshly generated
    # section notes, not trusted vault notes. Exempt them so a trusted note whose stem
    # collides with a generated section filename does not block an otherwise valid ingest.
    local_targets = _local_note_targets(ingestion_dir)

    for path in markdown_paths:
        relative = path.relative_to(ingestion_dir).as_posix()
        text = path.read_text(encoding="utf-8")
        frontmatter = _frontmatter(text)
        if not frontmatter:
            raise IngestionContractError(f"{relative} is missing YAML frontmatter")
        fields = _frontmatter_fields(frontmatter)
        _require_field(fields, relative, "status", "ingested")
        _require_field(fields, relative, "origin", origin)
        _require_field(fields, relative, "ingest_run_id", ingest_run_id)
        _require_field(fields, relative, "source_pdf", source_pdf_text)
        if _requires_source_section(path):
            _require_non_empty_field(fields, relative, "source_section")
        if "section" in fields:
            raise IngestionContractError(
                f"{relative} uses legacy section field; use source_section instead"
            )
        _reject_trusted_wikilinks(text, relative, trusted_targets, local_targets)


def _normal_markdown_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.rglob("*.md") if not path.name.startswith("_")))


def _local_note_targets(ingestion_dir: Path) -> set[str]:
    """Normalized wikilink targets for notes generated inside this ingestion folder."""
    root = ingestion_dir.resolve(strict=False)
    targets: set[str] = set()
    for path in sorted(root.rglob("*.md")):
        resolved = path.resolve(strict=False)
        relative = resolved.relative_to(root).with_suffix("").as_posix()
        targets.add(_normalize_wikilink_target(relative))
        targets.add(_normalize_wikilink_target(resolved.stem))
    return {target for target in targets if target}


def _requires_source_section(path: Path) -> bool:
    return path.name not in {"index.md", "00_metadata.md"}


def _validate_uuid(value: str) -> None:
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise IngestionContractError(f"ingest_run_id is not a valid UUID: {value}") from exc


def _normalize_source_pdf(source_pdf: Path | str) -> str:
    if isinstance(source_pdf, Path):
        return source_pdf.expanduser().resolve(strict=False).as_posix()
    return str(source_pdf)


def _frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    rest = text.removeprefix("---\n")
    frontmatter, sep, _body = rest.partition("\n---\n")
    return frontmatter if sep else ""


def _frontmatter_fields(frontmatter: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in frontmatter.splitlines():
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*?)\s*$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip("\"'")
    return fields


def _require_field(fields: dict[str, str], relative: str, key: str, expected: str) -> None:
    actual = fields.get(key)
    if actual != expected:
        raise IngestionContractError(
            f"{relative} must include {key}: {expected}; found {actual or 'missing'}"
        )


def _require_non_empty_field(fields: dict[str, str], relative: str, key: str) -> None:
    if not fields.get(key):
        raise IngestionContractError(f"{relative} must include non-empty {key}")


def _reject_trusted_wikilinks(
    text: str,
    relative: str,
    trusted_targets: set[str] | None,
    local_targets: set[str],
) -> None:
    targets = _wikilink_targets(text) - local_targets
    blocked = targets if trusted_targets is None else targets.intersection(trusted_targets)
    if blocked:
        rendered = ", ".join(sorted(blocked))
        raise IngestionContractError(
            f"{relative} links to trusted notes before the explicit linking/promotion phase: "
            f"{rendered}"
        )


def _wikilink_targets(text: str) -> set[str]:
    targets: set[str] = set()
    for match in re.finditer(r"\[\[([^\]]+)\]\]", text):
        raw_target = match.group(1).split("|", 1)[0].split("#", 1)[0].strip()
        normalized = _normalize_wikilink_target(raw_target)
        if normalized:
            targets.add(normalized)
    return targets


def _trusted_wikilink_targets(vault_root: Path | str) -> set[str]:
    vault = Path(vault_root).expanduser().resolve(strict=False)
    targets: set[str] = set()
    for path in sorted(vault.rglob("*.md")):
        resolved = path.resolve(strict=False)
        if _is_untrusted_workspace_note(vault, resolved):
            continue
        relative = resolved.relative_to(vault).with_suffix("").as_posix()
        targets.add(_normalize_wikilink_target(relative))
        targets.add(_normalize_wikilink_target(resolved.stem))
    return {target for target in targets if target}


def _is_untrusted_workspace_note(vault: Path, path: Path) -> bool:
    relative = path.relative_to(vault)
    return bool(relative.parts and relative.parts[0] in {"90_Staging", "91_Ingestion"})


def _normalize_wikilink_target(target: str) -> str:
    return re.sub(r"\s+", " ", target).strip().casefold()
