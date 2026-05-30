"""Shared deterministic Obsidian inventory primitives."""

from obsidian_inventory.scanner import (
    VALID_SCOPES,
    IndexRecord,
    IndexSummary,
    build_index,
    extract_aliases,
    extract_frontmatter,
    extract_headings,
    normalize_wikilink_target,
    scope_for_path,
)

__all__ = [
    "IndexRecord",
    "IndexSummary",
    "VALID_SCOPES",
    "build_index",
    "extract_aliases",
    "extract_frontmatter",
    "extract_headings",
    "normalize_wikilink_target",
    "scope_for_path",
]
