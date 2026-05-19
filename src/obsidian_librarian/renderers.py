"""Markdown renderers for staged Obsidian notes."""

from __future__ import annotations

import json
import re
from pathlib import Path

from obsidian_librarian.models import SourceDocument

_SAFE_PART_RE = re.compile(r"[^A-Za-z0-9._-]+")


def yaml_string(value: str) -> str:
    """Return a conservative quoted scalar suitable for simple YAML frontmatter."""
    return json.dumps(value, ensure_ascii=False)


def sanitize_path_part(value: str) -> str:
    """Sanitize one path segment for generated staged files."""
    cleaned = _SAFE_PART_RE.sub("-", value.strip()).strip(".-_ ")
    return cleaned or "untitled"


def staged_source_note_path(source: SourceDocument) -> Path:
    """Return the relative staged path for a source note."""
    parent_parts = [sanitize_path_part(part) for part in source.relative_path.parent.parts]
    suffix = sanitize_path_part(source.relative_path.suffix.lstrip(".") or "file")
    stem = sanitize_path_part(source.relative_path.stem)
    filename = f"{stem}_{suffix}.source.md"
    return Path("Sources", *parent_parts, filename)


def render_source_note(source: SourceDocument) -> str:
    """Render a staged source note from a parsed source document."""
    action_items = render_action_items(source.action_items)
    source_path = source.relative_path.as_posix()

    return (
        "---\n"
        "type: \"source\"\n"
        f"source_kind: {yaml_string(source.source_kind)}\n"
        f"source_path: {yaml_string(source_path)}\n"
        "project: \"unknown\"\n"
        "status: \"staged\"\n"
        "confidence: \"source-backed\"\n"
        "---\n\n"
        f"# {source.title}\n\n"
        "## Summary\n\n"
        "No deterministic summary generated in Phase 3.\n\n"
        "## Key claims\n\n"
        "No key claims extracted deterministically in Phase 3.\n\n"
        "## Action items\n\n"
        f"{action_items}\n\n"
        "## Open questions\n\n"
        "No open questions extracted deterministically in Phase 3.\n\n"
        "## Source excerpt\n\n"
        f"{render_excerpt(source.content)}\n\n"
        "## Links\n\n"
        f"- Source path: `{source_path}`\n"
    )


def render_action_items(items: tuple[str, ...]) -> str:
    """Render extracted action items."""
    if not items:
        return "No action items extracted deterministically."

    return "\n".join(f"- {item}" for item in items)


def render_excerpt(content: str, max_chars: int = 1200) -> str:
    """Render a bounded source excerpt."""
    normalized = content.strip()
    if not normalized:
        return "Source file is empty."

    excerpt = normalized[:max_chars]
    if len(normalized) > max_chars:
        excerpt = f"{excerpt}\n\n... excerpt truncated ..."

    return f"```text\n{excerpt}\n```"
