"""Deterministic read-only vault indexer."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from obsidian_librarian.validators import parse_frontmatter

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
TAG_RE = re.compile(r"(?:^|\s)#([A-Za-z0-9_/-]+)")
SOURCE_REF_RE = re.compile(r"`([^`]+)`")


@dataclass(frozen=True)
class IndexRecord:
    path: str
    scope: str
    title: str
    headings: list[str]
    tags: list[str]
    wikilinks: list[str]
    frontmatter: dict[str, str]
    source_refs: list[str]
    status: str
    modified_time: str
    snippets: list[str]


@dataclass
class IndexSummary:
    root: Path
    scope: str
    scanned_files: int = 0
    indexed_records: list[IndexRecord] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)


def build_index(vault_root: str | Path, scope: str) -> IndexSummary:
    root = Path(vault_root).expanduser().resolve(strict=False)
    if not root.exists():
        raise FileNotFoundError(f"Vault root does not exist: {root}")
    if scope not in {"vault", "staging", "vault-and-staging"}:
        raise ValueError(f"Invalid scope: {scope}")

    summary = IndexSummary(root=root, scope=scope)
    for file_path in sorted(root.rglob("*.md")):
        if not file_path.is_file():
            continue
        file_scope = _scope_for_path(root, file_path)
        if not _scope_included(scope, file_scope):
            summary.skipped_files.append(file_path)
            continue

        summary.scanned_files += 1
        content = file_path.read_text(encoding="utf-8")
        frontmatter = _safe_frontmatter(content)
        title = _extract_title(content, file_path)
        headings = [line[3:].strip() for line in content.splitlines() if line.startswith("## ")]
        tags = sorted(set(TAG_RE.findall(content)))
        wikilinks = sorted(set(WIKILINK_RE.findall(content)))
        source_refs = sorted(set(SOURCE_REF_RE.findall(content)))
        status = frontmatter.get("status", "staged" if file_scope == "staging" else "trusted")
        modified_time = datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC).isoformat()
        snippet = content.strip().replace("\n", " ")[:240]

        summary.indexed_records.append(
            IndexRecord(
                path=file_path.relative_to(root).as_posix(),
                scope=file_scope,
                title=title,
                headings=headings,
                tags=tags,
                wikilinks=wikilinks,
                frontmatter=frontmatter,
                source_refs=source_refs,
                status=status,
                modified_time=modified_time,
                snippets=[snippet] if snippet else [],
            )
        )

    return summary


def _scope_for_path(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    return "staging" if rel.parts and rel.parts[0] == "90_Staging" else "vault"


def _scope_included(scope: str, file_scope: str) -> bool:
    return (scope == "vault-and-staging") or (scope == file_scope)


def _safe_frontmatter(content: str) -> dict[str, str]:
    try:
        return parse_frontmatter(content)
    except ValueError:
        return {}


def _extract_title(content: str, path: Path) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem
