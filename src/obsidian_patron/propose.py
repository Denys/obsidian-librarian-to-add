from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from obsidian_inventory import build_index, extract_frontmatter
from obsidian_patron.classifier import (
    build_proposal_markdown,
    classify_hub,
    extract_tags,
    load_hub_config,
)
from obsidian_patron.safety import ensure_under


def generate_proposal(
    slug: str,
    vault_root: str | Path,
    *,
    allow_new_tags: bool = False,
    use_llm: bool = False,
    model: str = "gpt-5.4-mini",
) -> Path:
    vault = Path(vault_root).expanduser().resolve(strict=False)
    ingestion_root = (vault / "91_Ingestion").resolve(strict=False)
    slug_dir = ensure_under(ingestion_root, ingestion_root / slug)
    if not slug_dir.exists():
        raise FileNotFoundError(f"Ingestion slug not found: {slug_dir}")

    title = slug
    text, metadata_text = _proposal_source_text(slug_dir)
    manifest = _read_manifest(slug_dir)
    filename = str(manifest.get("source_pdf") or slug)
    existing_tags = _existing_vault_tags(vault)
    config = load_hub_config()

    selected, ranked = classify_hub(
        title=title,
        text=text,
        metadata_text=metadata_text,
        filename=filename,
        config=config,
    )
    tags = extract_tags(
        title=title,
        text=text,
        metadata_text=metadata_text,
        filename=filename,
        existing_tags=existing_tags,
        allow_new_tags=allow_new_tags,
        config=config,
    )
    llm_section, warning = _llm_enrichment(
        title=title,
        text=text,
        selected_hub=selected,
        tags=tags,
        model=model,
    ) if use_llm else (None, None)
    proposal = build_proposal_markdown(
        slug_dir=slug_dir,
        classification=selected,
        ranked=ranked,
        tags=tags,
        allow_new_tags=allow_new_tags,
        llm_section=llm_section,
        warning=warning,
    )
    proposal_path = slug_dir / "_proposal.md"
    proposal_path.write_text(proposal, encoding="utf-8")
    return proposal_path


def _proposal_source_text(slug_dir: Path) -> tuple[str, str]:
    body_parts: list[str] = []
    metadata_parts: list[str] = []
    for path in sorted(slug_dir.glob("*.md")):
        if path.name in {"_proposal.md", "_unmatched_candidates.md"}:
            continue
        text = path.read_text(encoding="utf-8")
        if path.name == "00_metadata.md":
            metadata_parts.append(text)
        else:
            body_parts.append(text)
        frontmatter = extract_frontmatter(text)
        if frontmatter:
            metadata_parts.append(" ".join(str(value) for value in frontmatter.values()))
    manifest = _read_manifest(slug_dir)
    if manifest:
        metadata_parts.append(json.dumps(manifest, sort_keys=True))
    return "\n\n".join(body_parts), "\n\n".join(metadata_parts)


def _read_manifest(slug_dir: Path) -> dict[str, Any]:
    manifest_path = slug_dir / "_ingest_manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _existing_vault_tags(vault: Path) -> set[str]:
    records = build_index(vault, "vault-and-staging").indexed_records
    return {tag for record in records for tag in record.tags}


def _llm_enrichment(
    *,
    title: str,
    text: str,
    selected_hub: str,
    tags: tuple[str, ...],
    model: str,
) -> tuple[str | None, str | None]:
    if not os.environ.get("OPENAI_API_KEY"):
        return None, "LLM enrichment skipped: OPENAI_API_KEY is not set"
    try:
        from openai import OpenAI
    except Exception:
        return None, "LLM enrichment skipped: OpenAI SDK is not installed"
    try:
        client = OpenAI()
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Return concise proposal-only markdown. Do not claim source evidence. "
                        "Use headings: suggested_hub, abstract, llm_suggested_tags."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Title: {title}\nDeterministic hub: {selected_hub}\n"
                        f"Deterministic tags: {', '.join(tags) or 'none'}\n\n"
                        f"Content excerpt:\n{text[:6000]}"
                    ),
                },
            ],
        )
        output = getattr(response, "output_text", "") or ""
        if not output.strip():
            return None, "LLM enrichment skipped: response did not include text"
    except Exception as exc:
        return None, f"LLM enrichment skipped: {exc}"
    return "## LLM enrichment\n\n" + output.strip() + "\n", None
