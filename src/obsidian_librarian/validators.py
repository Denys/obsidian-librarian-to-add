"""Deterministic validators for staged Obsidian notes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_FIELDS_BY_TYPE = {
    "source": ("type", "source_kind", "source_path", "status", "confidence"),
    "atomic": ("type", "source_path", "status", "confidence"),
    "action_extract": ("type", "source_path", "status"),
    "uncertainty": ("type", "source_path", "status"),
}

REQUIRED_SECTIONS_BY_TYPE = {
    "source": (
        "## Summary",
        "## Key claims",
        "## Action items",
        "## Open questions",
        "## Links",
    ),
    "atomic": (
        "## Definition",
        "## Why it matters",
        "## Evidence",
        "## Related",
    ),
}

REPORT_FILE_PREFIX = "review_report"


@dataclass(frozen=True)
class ValidationIssue:
    """One validation issue found in a staged note."""

    path: Path
    message: str
    severity: str = "error"


@dataclass
class ValidationSummary:
    """Validation result for one file or directory."""

    root: Path
    checked_files: list[Path] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return true when no validation issues were found."""
        return not self.issues


def validate_path(path: str | Path) -> ValidationSummary:
    """Validate one Markdown file or all Markdown files under a directory."""
    root = Path(path).expanduser().resolve(strict=False)

    if not root.exists():
        raise FileNotFoundError(f"Validation path does not exist: {root}")

    candidates = [root] if root.is_file() else sorted(root.rglob("*.md"))
    summary = ValidationSummary(root=root)

    for candidate in candidates:
        if not candidate.is_file() or candidate.suffix.lower() != ".md":
            continue
        if should_skip_validation(candidate):
            summary.skipped_files.append(candidate)
            continue
        summary.checked_files.append(candidate)
        summary.issues.extend(validate_note(candidate))

    return summary


def should_skip_validation(path: Path) -> bool:
    """Return true for generated Markdown files that are not staged notes."""
    return path.stem.startswith(REPORT_FILE_PREFIX)


def validate_note(path: Path) -> list[ValidationIssue]:
    """Validate one staged Markdown note."""
    content = path.read_text(encoding="utf-8")
    issues: list[ValidationIssue] = []

    try:
        frontmatter = parse_frontmatter(content)
    except ValueError as exc:
        return [ValidationIssue(path=path, message=str(exc))]

    note_type = frontmatter.get("type")
    if not note_type:
        issues.append(
            ValidationIssue(path=path, message="Missing required frontmatter field: type")
        )
        return issues

    required_fields = REQUIRED_FIELDS_BY_TYPE.get(note_type)
    if required_fields is None:
        issues.append(ValidationIssue(path=path, message=f"Unknown note type: {note_type}"))
        return issues

    for field_name in required_fields:
        if not frontmatter.get(field_name):
            issues.append(
                ValidationIssue(
                    path=path,
                    message=f"Missing required frontmatter field: {field_name}",
                )
            )

    for section in REQUIRED_SECTIONS_BY_TYPE.get(note_type, ()):  # optional by type
        if section not in content:
            issues.append(
                ValidationIssue(path=path, message=f"Missing required section: {section}")
            )

    if frontmatter.get("status") != "staged":
        issues.append(ValidationIssue(path=path, message="Generated note status must be staged"))

    return issues


def parse_frontmatter(content: str) -> dict[str, str]:
    """Parse simple YAML-like frontmatter without external dependencies."""
    lines = content.splitlines()

    if not lines or lines[0].strip() != "---":
        raise ValueError("Missing frontmatter opening delimiter")

    try:
        closing_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration as exc:
        raise ValueError("Missing frontmatter closing delimiter") from exc

    frontmatter: dict[str, str] = {}
    for line in lines[1:closing_index]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise ValueError(f"Invalid frontmatter line: {line}")
        key, value = stripped.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"').strip("'")

    return frontmatter


def render_validation_summary(summary: ValidationSummary) -> str:
    """Render a compact Markdown validation summary."""
    lines = [
        "# Obsidian Librarian Validation Report",
        "",
        f"- Root: `{summary.root}`",
        f"- Checked Markdown files: {len(summary.checked_files)}",
        f"- Skipped Markdown files: {len(summary.skipped_files)}",
        f"- Issues: {len(summary.issues)}",
        "",
    ]

    if summary.passed:
        lines.append("Validation passed.")
        return "\n".join(lines)

    lines.append("## Issues")
    lines.append("")
    for issue in summary.issues:
        lines.append(f"- `{issue.path}` — {issue.severity}: {issue.message}")

    return "\n".join(lines)
