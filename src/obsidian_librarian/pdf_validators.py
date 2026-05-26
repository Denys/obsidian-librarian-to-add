"""Deterministic validators for staged PDF manifests and artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any

PDF_ALLOWED_STATUSES = {"staged", "needs_review", "skipped", "failed"}
PDF_ALLOWED_EXTRACTION_METHODS = {"classifier_probe", "docling"}
PDF_SCHEMA_VERSION = 1
PDF_HEX_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PDF_ARTIFACT_FILENAMES = {
    "manifest.json",
    "source.md",
    "docling.json",
    "tables.json",
}


@dataclass(frozen=True)
class PdfValidationIssue:
    """One validation issue found in staged PDF artifacts."""

    path: Path
    message: str
    severity: str = "error"


@dataclass
class PdfValidationSummary:
    """Validation result for staged PDF manifests and artifacts."""

    root: Path
    checked_manifests: list[Path] = field(default_factory=list)
    checked_artifact_dirs: list[Path] = field(default_factory=list)
    issues: list[PdfValidationIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return true when no PDF validation issues were found."""
        return not self.issues


def validate_pdf_staging_path(path: str | Path) -> PdfValidationSummary:
    """Validate staged PDF manifests and generated artifact references.

    The input can be a staging root, a `pdf/` staging subtree, one PDF artifact
    directory, or one `manifest.json` file. Output paths recorded in manifests
    are always resolved relative to the inferred staging root.
    """
    root = Path(path).expanduser().resolve(strict=False)
    if not root.exists():
        raise FileNotFoundError(f"PDF validation path does not exist: {root}")

    staging_root = infer_staging_root(root)
    summary = PdfValidationSummary(root=root)

    if root.is_file():
        if root.name != "manifest.json":
            raise ValueError(f"PDF validation only supports manifest.json files, got: {root}")
        summary.checked_manifests.append(root)
        summary.issues.extend(validate_pdf_manifest(root, staging_root))
        return summary

    for artifact_dir in discover_pdf_artifact_dirs(root):
        summary.checked_artifact_dirs.append(artifact_dir)
        manifest = artifact_dir / "manifest.json"
        if not manifest.exists():
            summary.issues.append(
                PdfValidationIssue(
                    artifact_dir,
                    "Missing required PDF manifest: manifest.json",
                )
            )
            continue
        summary.checked_manifests.append(manifest)
        summary.issues.extend(validate_pdf_manifest(manifest, staging_root))

    return summary


def infer_staging_root(path: Path) -> Path:
    """Infer the `90_Staging` root for a PDF validation path."""
    current = path if path.is_dir() else path.parent
    if current.name == "90_Staging":
        return current
    for parent in (current, *current.parents):
        if parent.name == "90_Staging":
            return parent
    if current.name == "pdf":
        return current.parent
    if current.name == "manifest.json":
        return current.parent.parent.parent
    if (current / "manifest.json").exists() and current.parent.name == "pdf":
        return current.parent.parent
    return current


def discover_pdf_artifact_dirs(path: Path) -> list[Path]:
    """Return likely staged PDF artifact directories under a validation path."""
    root = path.resolve(strict=False)
    if (root / "manifest.json").exists():
        return [root]

    pdf_root = root if root.name == "pdf" else root / "pdf"
    if not pdf_root.exists() or not pdf_root.is_dir():
        return []

    artifact_dirs: list[Path] = []
    for candidate in sorted(item for item in pdf_root.rglob("*") if item.is_dir()):
        child_paths = list(candidate.iterdir())
        child_dirs = [child for child in child_paths if child.is_dir()]
        has_artifact = any(
            child.is_file() and child.name in PDF_ARTIFACT_FILENAMES
            for child in child_paths
        )
        has_assets = any(child.is_dir() and child.name == "assets" for child in child_paths)
        if has_artifact or has_assets or not child_dirs:
            artifact_dirs.append(candidate)

    return artifact_dirs


def validate_pdf_manifest(
    manifest_path: str | Path, staging_root: str | Path
) -> list[PdfValidationIssue]:
    """Validate one PDF manifest and its claimed generated outputs."""
    path = Path(manifest_path).expanduser().resolve(strict=False)
    staging = Path(staging_root).expanduser().resolve(strict=False)
    issues: list[PdfValidationIssue] = []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [PdfValidationIssue(path, f"Invalid JSON manifest: {exc.msg}")]
    except OSError as exc:
        return [PdfValidationIssue(path, f"Cannot read PDF manifest: {exc}")]

    if not isinstance(payload, dict):
        return [PdfValidationIssue(path, "PDF manifest must be a JSON object")]

    issues.extend(_validate_manifest_schema(path, payload))

    extraction = payload.get("extraction")
    extraction = extraction if isinstance(extraction, dict) else None
    outputs = payload.get("outputs")
    outputs = outputs if isinstance(outputs, dict) else None
    if outputs is not None:
        issues.extend(_validate_outputs(path, staging, outputs))

    method = extraction.get("method") if extraction is not None else None
    status = payload.get("status")
    if method == "docling" and status not in {"failed", "skipped"}:
        issues.extend(_validate_docling_outputs_required(path, staging, outputs))

    if outputs is not None and outputs.get("markdown_note") is not None:
        markdown_path = _resolve_optional_output_path(
            path,
            staging,
            outputs.get("markdown_note"),
            "outputs.markdown_note",
            issues,
        )
        if markdown_path is not None and markdown_path.exists() and markdown_path.is_file():
            issues.extend(_validate_markdown_frontmatter(path, markdown_path, payload))

    return issues


def _validate_manifest_schema(path: Path, payload: dict[str, Any]) -> list[PdfValidationIssue]:
    issues: list[PdfValidationIssue] = []

    if payload.get("schema_version") != PDF_SCHEMA_VERSION:
        issues.append(path_issue(path, "schema_version must be 1"))

    if payload.get("source_kind") != "pdf":
        issues.append(path_issue(path, "source_kind must be pdf"))

    source_path = payload.get("source_path")
    if not isinstance(source_path, str) or not source_path:
        issues.append(path_issue(path, "source_path must be a non-empty string"))

    source_hash = payload.get("source_hash")
    if not isinstance(source_hash, str) or not PDF_HEX_SHA256_RE.match(source_hash):
        issues.append(path_issue(path, "source_hash must be a lowercase SHA-256 hex digest"))

    status = payload.get("status")
    if status not in PDF_ALLOWED_STATUSES:
        issues.append(path_issue(path, "status must be staged, needs_review, skipped, or failed"))

    classification = payload.get("classification")
    if not isinstance(classification, str) or not classification:
        issues.append(path_issue(path, "classification must be a non-empty string"))

    page_count = payload.get("page_count")
    if not isinstance(page_count, int):
        issues.append(path_issue(path, "page_count must be an integer"))
    elif status != "failed" and page_count <= 0:
        issues.append(
            path_issue(path, "page_count must be greater than zero unless status is failed")
        )
    elif status == "failed" and page_count < 0:
        issues.append(path_issue(path, "page_count must not be negative"))

    extraction = _object_field(path, payload, "extraction", issues)
    if extraction is not None:
        method = extraction.get("method")
        if method not in PDF_ALLOWED_EXTRACTION_METHODS:
            issues.append(path_issue(path, "extraction.method must be classifier_probe or docling"))
        if extraction.get("ocr_enabled") is not False:
            issues.append(path_issue(path, "extraction.ocr_enabled must remain false"))

    _object_field(path, payload, "outputs", issues)

    return issues


def _validate_outputs(
    manifest_path: Path,
    staging_root: Path,
    outputs: dict[str, Any],
) -> list[PdfValidationIssue]:
    issues: list[PdfValidationIssue] = []

    root = _resolve_required_output_path(
        manifest_path,
        staging_root,
        outputs.get("root"),
        "outputs.root",
        issues,
    )
    if root is not None and (not root.exists() or not root.is_dir()):
        issues.append(
            path_issue(manifest_path, f"outputs.root does not exist as a directory: {root}")
        )

    for key in ("markdown_note", "json_sidecar", "structured_json"):
        value = outputs.get(key)
        if value is None:
            continue
        resolved = _resolve_optional_output_path(
            manifest_path,
            staging_root,
            value,
            f"outputs.{key}",
            issues,
        )
        if resolved is not None and (not resolved.exists() or not resolved.is_file()):
            issues.append(
                path_issue(manifest_path, f"outputs.{key} does not exist as a file: {resolved}")
            )

    for key in ("table_sidecars", "tables"):
        values = outputs.get(key)
        if values is None:
            continue
        if not isinstance(values, list):
            issues.append(path_issue(manifest_path, f"outputs.{key} must be a list"))
            continue
        for value in values:
            resolved = _resolve_optional_output_path(
                manifest_path,
                staging_root,
                value,
                f"outputs.{key}",
                issues,
            )
            if resolved is not None and (not resolved.exists() or not resolved.is_file()):
                issues.append(
                    path_issue(
                        manifest_path,
                        f"outputs.{key} item does not exist as a file: {resolved}",
                    )
                )

    for key in ("asset_dir", "assets_dir"):
        value = outputs.get(key)
        if value is None:
            continue
        resolved = _resolve_optional_output_path(
            manifest_path,
            staging_root,
            value,
            f"outputs.{key}",
            issues,
        )
        if resolved is not None and (not resolved.exists() or not resolved.is_dir()):
            issues.append(
                path_issue(
                    manifest_path,
                    f"outputs.{key} does not exist as a directory: {resolved}",
                )
            )

    return issues


def _validate_docling_outputs_required(
    manifest_path: Path,
    staging_root: Path,
    outputs: dict[str, Any] | None,
) -> list[PdfValidationIssue]:
    if outputs is None:
        return [path_issue(manifest_path, "Docling extraction requires outputs")]

    issues: list[PdfValidationIssue] = []
    markdown = outputs.get("markdown_note")
    structured = outputs.get("json_sidecar") or outputs.get("structured_json")

    if not markdown:
        issues.append(
            path_issue(manifest_path, "Docling extraction requires outputs.markdown_note")
        )

    if not structured:
        issues.append(path_issue(manifest_path, "Docling extraction requires outputs.json_sidecar"))

    return issues


def _validate_markdown_frontmatter(
    manifest_path: Path,
    markdown_path: Path,
    manifest: dict[str, Any],
) -> list[PdfValidationIssue]:
    try:
        frontmatter = _parse_simple_frontmatter(markdown_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [PdfValidationIssue(markdown_path, f"PDF Markdown frontmatter invalid: {exc}")]

    expected = {
        "source_path": str(manifest.get("source_path")),
        "source_hash": str(manifest.get("source_hash")),
        "page_count": str(manifest.get("page_count")),
        "extraction_method": str(_nested_get(manifest, "extraction", "method")),
        "ocr_enabled": "false",
    }

    issues: list[PdfValidationIssue] = []
    for key, value in expected.items():
        if frontmatter.get(key) != value:
            issues.append(
                PdfValidationIssue(
                    markdown_path,
                    f"PDF Markdown frontmatter {key} does not match manifest {manifest_path.name}",
                )
            )
    return issues


def _parse_simple_frontmatter(content: str) -> dict[str, str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening delimiter")

    try:
        closing_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration as exc:
        raise ValueError("missing closing delimiter") from exc

    values: dict[str, str] = {}
    for line in lines[1:closing_index]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise ValueError(f"invalid line: {line}")
        key, value = stripped.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _object_field(
    path: Path,
    payload: dict[str, Any],
    key: str,
    issues: list[PdfValidationIssue],
) -> dict[str, Any] | None:
    value = payload.get(key)
    if not isinstance(value, dict):
        issues.append(path_issue(path, f"{key} must be an object"))
        return None
    return value


def _resolve_required_output_path(
    manifest_path: Path,
    staging_root: Path,
    value: Any,
    field_name: str,
    issues: list[PdfValidationIssue],
) -> Path | None:
    if not isinstance(value, str) or not value:
        issues.append(path_issue(manifest_path, f"{field_name} must be a non-empty relative path"))
        return None
    return _resolve_optional_output_path(manifest_path, staging_root, value, field_name, issues)


def _resolve_optional_output_path(
    manifest_path: Path,
    staging_root: Path,
    value: Any,
    field_name: str,
    issues: list[PdfValidationIssue],
) -> Path | None:
    if not isinstance(value, str) or not value:
        issues.append(path_issue(manifest_path, f"{field_name} must be a non-empty relative path"))
        return None

    if _is_unsafe_relative_path(value):
        issues.append(
            path_issue(manifest_path, f"{field_name} must stay under 90_Staging: {value}")
        )
        return None

    resolved = (staging_root / value).resolve(strict=False)
    if not resolved.is_relative_to(staging_root):
        issues.append(path_issue(manifest_path, f"{field_name} escapes 90_Staging: {value}"))
        return None
    return resolved


def _is_unsafe_relative_path(value: str) -> bool:
    posix_path = Path(value)
    windows_path = PureWindowsPath(value)
    if posix_path.is_absolute() or windows_path.is_absolute() or windows_path.drive:
        return True
    if any(part == ".." for part in posix_path.parts):
        return True
    return any(part == ".." for part in windows_path.parts)


def _nested_get(payload: dict[str, Any], section: str, key: str) -> Any:
    section_value = payload.get(section)
    if not isinstance(section_value, dict):
        return None
    return section_value.get(key)


def path_issue(path: Path, message: str) -> PdfValidationIssue:
    """Return a PDF validation issue for a path."""
    return PdfValidationIssue(path=path, message=message)
