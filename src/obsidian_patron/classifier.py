from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HubScore:
    hub: str
    score: int
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class HubRule:
    hub: str
    filename_regexes: tuple[str, ...]
    keywords: tuple[str, ...]
    metadata_keywords: tuple[str, ...]
    default_tags: tuple[str, ...]


@dataclass(frozen=True)
class HubConfig:
    threshold: int
    rules: tuple[HubRule, ...]


DEFAULT_HUB_KEYWORDS: dict[str, tuple[str, ...]] = {
    "10_DSP-Eurorack": ("dsp", "filter", "oscillator", "audio", "reverb", "delay"),
    "20_Power-Electronics": ("power", "converter", "buck", "boost", "voltage", "current"),
    "30_EMC": ("emc", "emi", "noise", "shielding", "compliance"),
}

DEFAULT_HUB_CONFIG = HubConfig(
    threshold=2,
    rules=tuple(
        HubRule(
            hub=hub,
            filename_regexes=(),
            keywords=words,
            metadata_keywords=words,
            default_tags=words,
        )
        for hub, words in DEFAULT_HUB_KEYWORDS.items()
    ),
)


def load_hub_config(path: str | Path | None = None) -> HubConfig:
    config_path = Path(path) if path else Path(__file__).parent / "config" / "hubs.yaml"
    if not config_path.exists():
        return DEFAULT_HUB_CONFIG
    try:
        import yaml
    except Exception:
        return DEFAULT_HUB_CONFIG
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    hubs = payload.get("hubs", {})
    rules: list[HubRule] = []
    if isinstance(hubs, dict):
        for hub, values in sorted(hubs.items()):
            values = values if isinstance(values, dict) else {}
            rules.append(
                HubRule(
                    hub=str(hub),
                    filename_regexes=_string_tuple(values.get("filename_regexes")),
                    keywords=_string_tuple(values.get("keywords")),
                    metadata_keywords=_string_tuple(values.get("metadata_keywords")),
                    default_tags=_string_tuple(values.get("default_tags")),
                )
            )
    threshold = payload.get("threshold", 2)
    return HubConfig(
        threshold=int(threshold) if isinstance(threshold, int) else 2,
        rules=tuple(rules) or DEFAULT_HUB_CONFIG.rules,
    )


def classify_hub(
    *,
    title: str,
    text: str,
    metadata_text: str = "",
    filename: str = "",
    config: HubConfig | None = None,
    hub_keywords: dict[str, tuple[str, ...]] | None = None,
) -> tuple[str, tuple[HubScore, ...]]:
    if hub_keywords is not None:
        config = HubConfig(
            threshold=1,
            rules=tuple(
                HubRule(
                    hub=hub,
                    filename_regexes=(),
                    keywords=words,
                    metadata_keywords=(),
                    default_tags=words,
                )
                for hub, words in hub_keywords.items()
            ),
        )
    config = config or load_hub_config()
    haystack = f"{title}\n{text}".lower()
    metadata_haystack = metadata_text.lower()
    scores: list[HubScore] = []
    for rule in config.rules:
        score = 0
        reasons: list[str] = []
        for pattern in rule.filename_regexes:
            if re.search(pattern, filename):
                score += 3
                reasons.append(f"filename:{pattern}")
        for word in rule.keywords:
            count = _count_token(haystack, word)
            if count:
                score += count
                reasons.append(f"keyword:{word}x{count}")
        for word in rule.metadata_keywords:
            count = _count_token(metadata_haystack, word)
            if count:
                score += count * 2
                reasons.append(f"metadata:{word}x{count}")
        scores.append(HubScore(hub=rule.hub, score=score, reasons=tuple(reasons)))
    ranked = tuple(sorted(scores, key=lambda s: (-s.score, s.hub)))
    top = ranked[0]
    tied = len(ranked) > 1 and ranked[1].score == top.score
    if top.score < config.threshold or tied:
        return "unclassified", ranked
    return top.hub, ranked


def extract_tags(
    *,
    title: str,
    text: str,
    metadata_text: str = "",
    filename: str = "",
    existing_tags: set[str] | None = None,
    allow_new_tags: bool = False,
    config: HubConfig | None = None,
) -> tuple[str, ...]:
    config = config or load_hub_config()
    existing_tags = existing_tags or set()
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", f"{title} {text}".lower())
    metadata_tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", metadata_text.lower()))
    filename_tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", filename.lower()))
    configured = {tag for rule in config.rules for tag in rule.default_tags}
    candidates = set(tokens).intersection(configured)
    candidates.update(metadata_tokens.intersection(configured))
    candidates.update(filename_tokens.intersection(configured))
    unique = sorted(candidates if allow_new_tags else candidates.intersection(existing_tags))
    return tuple(unique)


def _count_token(haystack: str, token: str) -> int:
    return len(re.findall(rf"\b{re.escape(token)}\b", haystack))


def build_proposal_markdown(
    *,
    slug_dir: Path,
    classification: str,
    ranked: tuple[HubScore, ...],
    tags: tuple[str, ...],
    allow_new_tags: bool = False,
    llm_section: str | None = None,
    warning: str | None = None,
) -> str:
    ranked_lines = "\n".join(
        f"- {s.hub}: {s.score}"
        + (f" ({'; '.join(s.reasons)})" if s.reasons else "")
        for s in ranked
    )
    tag_lines = "\n".join(f"- {t}" for t in tags) if tags else "- (none)"
    parts = [
        f"# Ingestion Proposal: {slug_dir.name}\n\n"
        "## Deterministic classification\n"
        f"- selected_hub: {classification}\n\n"
        "## Ranked hub candidates\n"
        f"{ranked_lines}\n\n"
        "## Deterministic tags\n"
        f"- allow_new_tags: {str(allow_new_tags).lower()}\n"
        f"{tag_lines}\n"
    ]
    if warning:
        parts.append(f"\n## Warnings\n- {warning}\n")
    if llm_section:
        parts.append(f"\n{llm_section.strip()}\n")
    return "".join(parts)


def _string_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, list | tuple):
        return tuple(str(item) for item in value if str(item).strip())
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    return ()
