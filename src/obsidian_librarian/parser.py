"""Deterministic Markdown/TXT inbox parser."""

from __future__ import annotations

from pathlib import Path

from obsidian_librarian.models import SkippedFile, SourceDocument

SUPPORTED_EXTENSIONS = {
    ".md": "markdown",
    ".txt": "text",
}


def parse_inbox(inbox_root: str | Path) -> tuple[list[SourceDocument], list[SkippedFile]]:
    """Parse supported source files from an inbox directory."""
    root = Path(inbox_root).expanduser().resolve(strict=False)

    if not root.exists():
        raise FileNotFoundError(f"Inbox directory does not exist: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"Inbox path is not a directory: {root}")

    documents: list[SourceDocument] = []
    skipped: list[SkippedFile] = []

    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        source_kind = SUPPORTED_EXTENSIONS.get(path.suffix.lower())
        if source_kind is None:
            skipped.append(SkippedFile(path=path, reason="unsupported extension"))
            continue

        documents.append(parse_source_file(path, root, source_kind))

    return documents, skipped


def parse_source_file(path: Path, inbox_root: Path, source_kind: str) -> SourceDocument:
    """Parse a single supported source file."""
    content = path.read_text(encoding="utf-8")
    relative_path = path.relative_to(inbox_root)

    return SourceDocument(
        path=path,
        relative_path=relative_path,
        source_kind=source_kind,
        title=extract_title(content, path),
        content=content,
        action_items=extract_action_items(content),
    )


def extract_title(content: str, path: Path) -> str:
    """Extract a conservative title from source content."""
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or path.stem
        return stripped[:80]

    return path.stem


def extract_action_items(content: str) -> tuple[str, ...]:
    """Extract obvious action items without model reasoning."""
    markers = ("todo:", "todo ", "- [ ]", "* [ ]", "- todo:", "* todo:")
    items: list[str] = []

    for line in content.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if any(lowered.startswith(marker) for marker in markers):
            items.append(stripped)

    return tuple(items)
