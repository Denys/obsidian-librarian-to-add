from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from obsidian_inventory import build_index, extract_frontmatter, extract_headings
from obsidian_patron.safety import ensure_under

GENERIC_HEADINGS = {
    "abstract",
    "appendix",
    "conclusion",
    "contents",
    "glossary",
    "index",
    "introduction",
    "overview",
    "references",
    "summary",
}


@dataclass(frozen=True)
class LinkResult:
    slug: str
    linked_files: tuple[Path, ...]
    unmatched_report: Path
    matched_count: int
    unmatched_count: int


@dataclass(frozen=True)
class Candidate:
    text: str
    source: Path
    source_section: str
    context: str


def link_ingested_notes(slug: str, vault_root: str | Path) -> LinkResult:
    vault = Path(vault_root).expanduser().resolve(strict=False)
    ingestion_root = (vault / "91_Ingestion").resolve(strict=False)
    slug_dir = ensure_under(ingestion_root, ingestion_root / slug)
    if not slug_dir.exists():
        raise FileNotFoundError(f"Ingestion slug not found: {slug_dir}")

    inventory = _build_match_inventory(vault=vault, slug_dir=slug_dir)
    note_paths = tuple(_iter_ingested_note_paths(slug_dir))
    candidates = _collect_candidates(note_paths)

    matched: dict[str, str] = {}
    unmatched: dict[str, list[Candidate]] = {}
    for candidate in candidates:
        key = candidate.text.casefold()
        if key in inventory:
            matched[candidate.text] = inventory[key]
        else:
            unmatched.setdefault(candidate.text, []).append(candidate)

    linked_files: list[Path] = []
    for note_path in note_paths:
        original = note_path.read_text(encoding="utf-8")
        updated = _insert_wikilinks(original, matched)
        if updated != original:
            note_path.write_text(updated, encoding="utf-8")
            linked_files.append(note_path)

    report_path = slug_dir / "_unmatched_candidates.md"
    report_path.write_text(_render_unmatched_report(unmatched), encoding="utf-8")

    return LinkResult(
        slug=slug,
        linked_files=tuple(linked_files),
        unmatched_report=report_path,
        matched_count=len(matched),
        unmatched_count=len(unmatched),
    )


def _iter_ingested_note_paths(slug_dir: Path) -> list[Path]:
    excluded = {"index.md", "00_metadata.md", "_proposal.md", "_unmatched_candidates.md"}
    return sorted(
        path
        for path in slug_dir.glob("*.md")
        if path.name not in excluded and not path.name.startswith("_")
    )


def _collect_candidates(note_paths: tuple[Path, ...]) -> tuple[Candidate, ...]:
    candidates: dict[tuple[str, Path], Candidate] = {}
    for path in note_paths:
        text = path.read_text(encoding="utf-8")
        source_section = _source_section(path, text)
        values = (
            _heading_candidates(text)
            + _bold_candidates(text)
            + _glossary_candidates(text)
            + _frequent_phrase_candidates(text)
        )
        for value in values:
            normalized = _normalize_candidate(value)
            if normalized:
                candidates[(normalized, path)] = Candidate(
                    normalized,
                    path,
                    source_section,
                    _example_context(text, normalized),
                )
    return tuple(
        candidates[key]
        for key in sorted(candidates, key=lambda item: (item[0].casefold(), item[1].as_posix()))
    )


def _heading_candidates(text: str) -> list[str]:
    return extract_headings(text)


def _bold_candidates(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"\*\*(.+?)\*\*", text)]


def _normalize_candidate(value: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", value).strip(" #`*_.,:;()[]{}")
    if not cleaned or len(cleaned) < 3 or "[[" in cleaned or "]]" in cleaned:
        return None
    return cleaned


def _build_match_inventory(*, vault: Path, slug_dir: Path) -> dict[str, str]:
    matches: dict[str, str] = {}
    records = build_index(vault, "vault-and-staging").indexed_records
    heading_targets: dict[str, set[str]] = {}
    for record in records:
        record_path = (vault / record.path).resolve(strict=False)
        if record_path.is_relative_to(slug_dir.resolve(strict=False)):
            continue
        _add_match(matches, record.title, record.title)
        _add_match(matches, Path(record.path).stem, record.title)
        for alias in record.aliases:
            _add_match(matches, alias, record.title)
        for heading in record.headings:
            normalized = _normalize_candidate(heading)
            if normalized and normalized.casefold() not in GENERIC_HEADINGS:
                heading_targets.setdefault(normalized.casefold(), set()).add(record.title)
    for heading, targets in heading_targets.items():
        if len(targets) == 1:
            matches.setdefault(heading, next(iter(targets)))
    return matches


def _add_match(matches: dict[str, str], candidate: str, target: str) -> None:
    normalized = _normalize_candidate(candidate)
    if normalized:
        matches.setdefault(normalized.casefold(), target)


def _insert_wikilinks(text: str, matched: dict[str, str]) -> str:
    updated = text
    for candidate, target in sorted(
        matched.items(), key=lambda item: (-len(item[0]), item[0].casefold())
    ):
        if f"[[{target}" in updated:
            continue
        updated = _replace_first_body_occurrence(updated, candidate, f"[[{target}|{candidate}]]")
    return updated


def _replace_first_body_occurrence(text: str, needle: str, replacement: str) -> str:
    lines = text.splitlines(keepends=True)
    pattern = re.compile(rf"(?<!\[\[)\b{re.escape(needle)}\b(?![^\[]*\]\])")
    in_frontmatter = False
    in_fenced_code = False
    if lines and lines[0].strip() == "---":
        in_frontmatter = True
    for index, line in enumerate(lines):
        if in_frontmatter:
            if index > 0 and line.strip() == "---":
                in_frontmatter = False
            continue
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fenced_code = not in_fenced_code
            continue
        if in_fenced_code:
            continue
        if line.lstrip().startswith("#"):
            continue
        new_line, replacements = pattern.subn(replacement, line, count=1)
        if replacements:
            lines[index] = new_line
            return "".join(lines)
    return text


def _source_section(path: Path, text: str) -> str:
    frontmatter = extract_frontmatter(text)
    return frontmatter.get("source_section") or path.stem


def _glossary_candidates(text: str) -> list[str]:
    if not re.search(r"^#{1,6}\s+(glossary|index)\b", text, re.IGNORECASE | re.MULTILINE):
        return []
    candidates: list[str] = []
    for match in re.finditer(r"^\s*[-*]\s+([^:\-\n]{3,80})(?::|\s+-)", text, re.MULTILINE):
        candidates.append(match.group(1).strip())
    return candidates


def _frequent_phrase_candidates(text: str) -> list[str]:
    body = re.sub(r"---\n.*?\n---\n", " ", text, count=1, flags=re.DOTALL)
    phrases = re.findall(
        r"\b(?:[A-Z][A-Za-z0-9_-]+|[a-z][a-z0-9_-]{3,})"
        r"(?:\s+(?:[A-Z][A-Za-z0-9_-]+|[a-z][a-z0-9_-]{3,})){1,3}\b",
        body,
    )
    counts: dict[str, int] = {}
    for phrase in phrases:
        words = [word.casefold() for word in phrase.split()]
        if any(word in {"this", "that", "with", "from", "into", "section"} for word in words):
            continue
        normalized = " ".join(phrase.split())
        counts[normalized] = counts.get(normalized, 0) + 1
    return [phrase for phrase, count in counts.items() if count >= 2]


def _example_context(text: str, candidate: str) -> str:
    compact = re.sub(r"\s+", " ", text)
    match = re.search(re.escape(candidate), compact, re.IGNORECASE)
    if not match:
        return ""
    start = max(0, match.start() - 60)
    end = min(len(compact), match.end() + 60)
    return compact[start:end].strip()


def _render_unmatched_report(unmatched: dict[str, list[Candidate]]) -> str:
    lines = ["# Candidate notes — review before creating manually", ""]
    if not unmatched:
        lines.append("- None")
        return "\n".join(lines) + "\n"
    for candidate in sorted(unmatched, key=str.casefold):
        entries = unmatched[candidate]
        sources = sorted({entry.source.name for entry in entries})
        sections = sorted({entry.source_section for entry in entries if entry.source_section})
        contexts = [entry.context for entry in entries if entry.context]
        lines.append(
            f"- {candidate} (frequency: {len(entries)}; sources: {', '.join(sources)}; "
            f"source_sections: {', '.join(sections) or 'unknown'})"
        )
        if contexts:
            lines.append(f"  - example: {contexts[0]}")
    return "\n".join(lines) + "\n"
