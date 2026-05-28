from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HubScore:
    hub: str
    score: int


DEFAULT_HUB_KEYWORDS: dict[str, tuple[str, ...]] = {
    "10_DSP-Eurorack": ("dsp", "filter", "oscillator", "audio", "reverb", "delay"),
    "20_Power-Electronics": ("power", "converter", "buck", "boost", "voltage", "current"),
    "30_EMC": ("emc", "emi", "noise", "shielding", "compliance"),
}


def classify_hub(
    *, title: str, text: str, hub_keywords: dict[str, tuple[str, ...]] | None = None
) -> tuple[str, tuple[HubScore, ...]]:
    keywords = hub_keywords or DEFAULT_HUB_KEYWORDS
    haystack = f"{title}\n{text}".lower()
    scores: list[HubScore] = []
    for hub, words in keywords.items():
        score = sum(_count_token(haystack, word) for word in words)
        scores.append(HubScore(hub=hub, score=score))
    ranked = tuple(sorted(scores, key=lambda s: (-s.score, s.hub)))
    top = ranked[0]
    if top.score <= 0:
        return "unclassified", ranked
    return top.hub, ranked


def extract_tags(*, title: str, text: str) -> tuple[str, ...]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", f"{title} {text}".lower())
    preferred = [t for t in tokens if t in {"dsp", "emc", "power", "converter", "reverb", "filter"}]
    unique = sorted(set(preferred))
    return tuple(unique)


def _count_token(haystack: str, token: str) -> int:
    return len(re.findall(rf"\b{re.escape(token)}\b", haystack))


def build_proposal_markdown(
    *, slug_dir: Path, classification: str, ranked: tuple[HubScore, ...], tags: tuple[str, ...]
) -> str:
    ranked_lines = "\n".join(f"- {s.hub}: {s.score}" for s in ranked)
    tag_lines = "\n".join(f"- {t}" for t in tags) if tags else "- (none)"
    return (
        f"# Ingestion Proposal: {slug_dir.name}\n\n"
        "## Deterministic classification\n"
        f"- selected_hub: {classification}\n\n"
        "## Ranked hub candidates\n"
        f"{ranked_lines}\n\n"
        "## Deterministic tags\n"
        f"{tag_lines}\n"
    )
