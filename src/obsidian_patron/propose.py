from __future__ import annotations

from pathlib import Path

from obsidian_patron.classifier import build_proposal_markdown, classify_hub, extract_tags
from obsidian_patron.safety import ensure_under


def generate_proposal(slug: str, vault_root: str | Path) -> Path:
    vault = Path(vault_root).expanduser().resolve(strict=False)
    ingestion_root = (vault / "91_Ingestion").resolve(strict=False)
    slug_dir = ensure_under(ingestion_root, ingestion_root / slug)
    if not slug_dir.exists():
        raise FileNotFoundError(f"Ingestion slug not found: {slug_dir}")

    title = slug
    index_path = slug_dir / "index.md"
    text = index_path.read_text(encoding="utf-8") if index_path.exists() else ""

    selected, ranked = classify_hub(title=title, text=text)
    tags = extract_tags(title=title, text=text)
    proposal = build_proposal_markdown(
        slug_dir=slug_dir,
        classification=selected,
        ranked=ranked,
        tags=tags,
    )
    proposal_path = slug_dir / "_proposal.md"
    proposal_path.write_text(proposal, encoding="utf-8")
    return proposal_path
