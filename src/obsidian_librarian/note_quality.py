"""Deterministic note-quality review for staged Obsidian notes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from obsidian_librarian.validators import parse_frontmatter, should_skip_validation

ACTION_CUE_RE = re.compile(
    r"\b(todo|to do|follow up|follow-up|action item|next step|call|email|schedule)\b",
    re.IGNORECASE,
)
SEMANTIC_OVERCLAIM_RE = re.compile(
    r"\b(semantic summary|llm summary|ai-generated summary|completed semantic summary)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NoteQualityFinding:
    """One deterministic quality finding."""

    path: Path
    check_id: str
    message: str
    severity: str = "blocking"


@dataclass
class NoteQualityResult:
    """Quality result for one staged note."""

    path: Path
    blocking_findings: list[NoteQualityFinding] = field(default_factory=list)
    suggestions: list[NoteQualityFinding] = field(default_factory=list)
    eval_candidates: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return true when no blocking quality findings were found."""
        return not self.blocking_findings


@dataclass
class NoteQualitySummary:
    """Quality result for a file tree."""

    root: Path
    checked_files: list[Path] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)
    blocking_findings: list[NoteQualityFinding] = field(default_factory=list)
    suggestions: list[NoteQualityFinding] = field(default_factory=list)
    eval_candidates: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return true when no blocking quality findings were found."""
        return not self.blocking_findings


def review_note_quality(path: str | Path) -> NoteQualityResult:
    """Review one Markdown note for deterministic staged-note quality."""
    note_path = Path(path).expanduser().resolve(strict=False)
    content = note_path.read_text(encoding="utf-8")
    result = NoteQualityResult(path=note_path)

    try:
        frontmatter = parse_frontmatter(content)
    except ValueError as exc:
        result.blocking_findings.append(
            NoteQualityFinding(
                path=note_path,
                check_id="invalid_frontmatter",
                message=str(exc),
            )
        )
        return result

    _check_required_frontmatter(result, frontmatter)
    _check_summary_honesty(result, content)
    _check_action_separation(result, content)
    _add_review_suggestions(result, frontmatter, content)

    return result


def review_note_quality_path(path: str | Path) -> NoteQualitySummary:
    """Review one Markdown file or all Markdown files under a directory."""
    root = Path(path).expanduser().resolve(strict=False)

    if not root.exists():
        raise FileNotFoundError(f"Quality review path does not exist: {root}")

    candidates = [root] if root.is_file() else sorted(root.rglob("*.md"))
    summary = NoteQualitySummary(root=root)

    for candidate in candidates:
        if not candidate.is_file() or candidate.suffix.lower() != ".md":
            continue
        if should_skip_validation(candidate):
            summary.skipped_files.append(candidate)
            continue
        summary.checked_files.append(candidate)
        result = review_note_quality(candidate)
        summary.blocking_findings.extend(result.blocking_findings)
        summary.suggestions.extend(result.suggestions)
        summary.eval_candidates.extend(result.eval_candidates)

    return summary


def _check_required_frontmatter(
    result: NoteQualityResult,
    frontmatter: dict[str, str],
) -> None:
    required = (
        ("type", "missing_type", "Missing required frontmatter field: type"),
        (
            "source_path",
            "missing_source_path",
            "Missing required frontmatter field: source_path",
        ),
        ("status", "missing_staged_status", "Missing required staged status"),
    )

    for field_name, check_id, message in required:
        if not frontmatter.get(field_name):
            result.blocking_findings.append(
                NoteQualityFinding(path=result.path, check_id=check_id, message=message)
            )

    if frontmatter.get("status") and frontmatter.get("status") != "staged":
        result.blocking_findings.append(
            NoteQualityFinding(
                path=result.path,
                check_id="missing_staged_status",
                message="Generated note status must be staged",
            )
        )


def _check_summary_honesty(result: NoteQualityResult, content: str) -> None:
    summary = _section_text(content, "## Summary")
    if SEMANTIC_OVERCLAIM_RE.search(summary):
        result.blocking_findings.append(
            NoteQualityFinding(
                path=result.path,
                check_id="summary_overclaims_semantic_extraction",
                message="Summary claims semantic extraction in a deterministic review path",
            )
        )


def _check_action_separation(result: NoteQualityResult, content: str) -> None:
    key_claims = _section_text(content, "## Key claims")
    action_items = _section_text(content, "## Action items")

    if ACTION_CUE_RE.search(key_claims) and _section_has_no_actions(action_items):
        result.blocking_findings.append(
            NoteQualityFinding(
                path=result.path,
                check_id="action_items_in_key_claims",
                message="Action-like content appears in Key claims while Action items is empty",
            )
        )


def _add_review_suggestions(
    result: NoteQualityResult,
    frontmatter: dict[str, str],
    content: str,
) -> None:
    if "[[" not in content:
        result.suggestions.append(
            NoteQualityFinding(
                path=result.path,
                check_id="missing_wikilinks",
                message="No wikilinks found; add links only where targets are meaningful",
                severity="suggestion",
            )
        )

    if not frontmatter.get("project") and "tags" not in frontmatter:
        result.suggestions.append(
            NoteQualityFinding(
                path=result.path,
                check_id="missing_retrieval_handles",
                message="No project or tags metadata found for retrieval",
                severity="suggestion",
            )
        )

    action_items = _section_text(content, "## Action items")
    if _section_has_no_actions(action_items) and not ACTION_CUE_RE.search(content):
        result.suggestions.append(
            NoteQualityFinding(
                path=result.path,
                check_id="no_actionability_signal",
                message="No actionability signal found; this is a review suggestion only",
                severity="suggestion",
            )
        )


def _section_text(content: str, heading: str) -> str:
    lines = content.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        return ""

    section_lines: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        section_lines.append(line)
    return "\n".join(section_lines).strip()


def _section_has_no_actions(section: str) -> bool:
    normalized = section.strip().lower()
    return not normalized or normalized.startswith("no action items extracted")
