"""Optional staged-note enrichment orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from obsidian_librarian.config import LibrarianConfig
from obsidian_librarian.extraction_schema import ExtractionPayload
from obsidian_librarian.extractors import Extractor
from obsidian_librarian.renderers import sanitize_path_part, yaml_string
from obsidian_librarian.vault import ObsidianVault


def _ensure_staging_scope(root: Path, vault: ObsidianVault) -> None:
    staging_root = vault.staging_root.resolve(strict=False)
    resolved = root.resolve(strict=False)
    target = resolved.parent if resolved.is_file() else resolved
    if not target.is_relative_to(staging_root):
        raise ValueError(f"Enrichment path must be within staging root: {staging_root}")


@dataclass(frozen=True)
class EnrichedNoteResult:
    source_path: Path
    output_path: Path | None
    success: bool
    message: str


@dataclass
class EnrichSummary:
    root: Path
    mode: str
    extractor: str
    model: str | None
    checked_files: list[Path] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)
    outputs: list[Path] = field(default_factory=list)
    failures: list[EnrichedNoteResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


def enrich_path(
    path: str | Path,
    *,
    vault_root: str | Path,
    mode: str,
    extractor: Extractor,
    model: str | None,
) -> EnrichSummary:
    root = Path(path).expanduser().resolve(strict=False)
    if not root.exists():
        raise FileNotFoundError(f"Enrichment path does not exist: {root}")

    config = LibrarianConfig(vault_root=Path(vault_root))
    vault = ObsidianVault(config)
    _ensure_staging_scope(root, vault)
    summary = EnrichSummary(root=root, mode=mode, extractor=extractor.name, model=model)

    candidates = [root] if root.is_file() else sorted(root.rglob("*.md"))
    for candidate in candidates:
        if candidate.suffix.lower() != ".md":
            continue
        if candidate.name.startswith("review_report") or "/Enriched/" in candidate.as_posix():
            summary.skipped_files.append(candidate)
            continue
        summary.checked_files.append(candidate)
        text = candidate.read_text(encoding="utf-8")
        source_ref = candidate.as_posix()
        try:
            payload = extractor.extract(text, source_ref)
        except Exception as exc:
            summary.failures.append(
                EnrichedNoteResult(candidate, None, False, f"Extraction failed: {exc}")
            )
            continue

        output_rel = Path("Enriched") / f"{sanitize_path_part(candidate.stem)}.enriched.md"
        rendered = render_enriched_note(candidate, payload, extractor.name, model)

        if mode == "read-only":
            summary.outputs.append(vault.resolve_staged_path(output_rel))
            continue

        out = vault.write_staged_text_unique(output_rel, rendered)
        summary.outputs.append(out.path)

    return summary


def render_enriched_note(
    source_path: Path,
    payload: ExtractionPayload,
    extractor_name: str,
    model: str | None,
) -> str:
    model_value = model or "n/a"
    return (
        "---\n"
        'type: "source"\n'
        f"source_kind: {yaml_string('enriched_markdown')}\n"
        f"source_path: {yaml_string(source_path.as_posix())}\n"
        'project: "unknown"\n'
        'status: "staged"\n'
        f"confidence: {yaml_string(str(payload.confidence))}\n"
        "---\n\n"
        f"# Enriched Note — {source_path.stem}\n\n"
        "## Summary\n\n"
        f"{payload.summary}\n\n"
        "## Key claims\n\n"
        + "\n".join(f"- {x}" for x in payload.key_claims)
        + "\n\n## Action items\n\n"
        + "\n".join(f"- {x}" for x in payload.action_items)
        + "\n\n## Entities\n\n"
        + "\n".join(f"- {x}" for x in payload.entities)
        + "\n\n## Assumptions\n\n"
        + "\n".join(f"- {x}" for x in payload.assumptions)
        + "\n\n## Source references\n\n"
        + "\n".join(f"- {x}" for x in payload.source_refs)
        + "\n\n## Extraction metadata\n\n"
        + f"- Extractor: `{extractor_name}`\n"
        + f"- Model: `{model_value}`\n"
        + f"- Risk level: `{payload.risk_level}`\n"
        + f"- Confidence: `{payload.confidence}`\n"
        + "- Deterministic baseline preserved; review before promotion.\n"
    )
