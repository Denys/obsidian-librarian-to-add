from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from obsidian_patron.safety import ensure_under


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
    unmatched: dict[str, list[Path]] = {}
    for candidate in candidates:
        key = candidate.text.casefold()
        if key in inventory:
            matched[candidate.text] = inventory[key]
        else:
            unmatched.setdefault(candidate.text, []).append(candidate.source)

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
        for value in _heading_candidates(text) + _bold_candidates(text):
            normalized = _normalize_candidate(value)
            if normalized:
                candidates[(normalized, path)] = Candidate(normalized, path)
    return tuple(
        candidates[key]
        for key in sorted(candidates, key=lambda item: (item[0].casefold(), item[1].as_posix()))
    )


def _heading_candidates(text: str) -> list[str]:
    return [
        match.group(1).strip() for match in re.finditer(r"^#{1,6}\s+(.+?)\s*$", text, re.MULTILINE)
    ]


def _bold_candidates(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"\*\*(.+?)\*\*", text)]


def _normalize_candidate(value: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", value).strip(" #`*_.,:;()[]{}")
    if not cleaned or len(cleaned) < 3 or "[[" in cleaned or "]]" in cleaned:
        return None
    return cleaned


def _build_match_inventory(*, vault: Path, slug_dir: Path) -> dict[str, str]:
    matches: dict[str, str] = {}
    for path in sorted(vault.rglob("*.md")):
        resolved = path.resolve(strict=False)
        if resolved.is_relative_to(slug_dir.resolve(strict=False)):
            continue
        relative = resolved.relative_to(vault)
        if relative.parts and relative.parts[0] == "91_Ingestion":
            continue
        text = path.read_text(encoding="utf-8")
        title = _frontmatter_value(text, "title") or path.stem
        _add_match(matches, title, title)
        _add_match(matches, path.stem, title)
        for alias in _frontmatter_list(text, "aliases"):
            _add_match(matches, alias, title)
        for heading in _heading_candidates(text):
            _add_match(matches, heading, title)
    return matches


def _frontmatter_value(text: str, key: str) -> str | None:
    frontmatter = _frontmatter(text)
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", frontmatter, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip("\"'")


def _frontmatter_list(text: str, key: str) -> tuple[str, ...]:
    frontmatter = _frontmatter(text)
    inline = re.search(rf"^{re.escape(key)}:\s*\[(.*?)\]\s*$", frontmatter, re.MULTILINE)
    if inline:
        return tuple(
            item.strip().strip("\"'") for item in inline.group(1).split(",") if item.strip()
        )
    block = re.search(rf"^{re.escape(key)}:\s*\n((?:\s+-\s+.+\n?)*)", frontmatter, re.MULTILINE)
    if not block:
        return ()
    return tuple(
        line.split("-", 1)[1].strip().strip("\"'")
        for line in block.group(1).splitlines()
        if line.strip().startswith("-")
    )


def _frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    _, _, rest = text.partition("---\n")
    frontmatter, sep, _body = rest.partition("\n---\n")
    return frontmatter if sep else ""


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


def _render_unmatched_report(unmatched: dict[str, list[Path]]) -> str:
    lines = ["# Candidate notes - review before creating manually", ""]
    if not unmatched:
        lines.append("- None")
        return "\n".join(lines) + "\n"
    for candidate in sorted(unmatched, key=str.casefold):
        sources = sorted({path.name for path in unmatched[candidate]})
        lines.append(
            f"- {candidate} (frequency: {len(unmatched[candidate])}; sources: {', '.join(sources)})"
        )
    return "\n".join(lines) + "\n"
