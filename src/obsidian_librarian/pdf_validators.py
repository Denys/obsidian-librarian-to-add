"""Deterministic validators for staged PDF manifests and artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any

PDF_ALLOWED_STATUSES = {"staged", "needs_review", "skipped", "failed"}
PDF_ALLOWED_EXTRACTION_METHODS = {"classifier_probe", "docling", "ocr"}
PDF_SCHEMA_VERSION = 1
PDF_HEX_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PDF_ARTIFACT_FILENAMES = {
    "manifest.json",
    "source.md",
    "docling.json",
    "tables.json",
}
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


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
        if _is_nested_inside_artifact_dir(candidate, pdf_root):
            continue

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


def _is_nested_inside_artifact_dir(candidate: Path, pdf_root: Path) -> bool:
    """Return true when a directory is inside an already discovered artifact dir."""
    for parent in candidate.parents:
        if parent == pdf_root:
            return False
        if (parent / "manifest.json").exists():
            return True
    return False


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
    if method in {"docling", "ocr"} and status not in {"failed", "skipped"}:
        issues.extend(_validate_docling_outputs_required(path, staging, outputs))
        if outputs is not None:
            issues.extend(_validate_docling_table_sidecars(path, staging, outputs))
    if method == "ocr" and status not in {"needs_review", "failed", "skipped"}:
        issues.append(path_issue(path, "OCR extraction requires status needs_review"))

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
            if method in {"docling", "ocr"} and status not in {"failed", "skipped"}:
                issues.extend(
                    _validate_pdf_markdown_artifact_links(
                        path,
                        staging,
                        outputs,
                        markdown_path,
                    )
                )

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
            issues.append(
                path_issue(path, "extraction.method must be classifier_probe, docling, or ocr")
            )
        ocr_enabled = extraction.get("ocr_enabled")
        if method == "ocr":
            if ocr_enabled is not True:
                issues.append(path_issue(path, "OCR extraction requires ocr_enabled true"))
        elif ocr_enabled is not False:
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


def _validate_docling_table_sidecars(
    manifest_path: Path,
    staging_root: Path,
    outputs: dict[str, Any],
) -> list[PdfValidationIssue]:
    table_values = outputs.get("table_sidecars") or outputs.get("tables") or []
    if not isinstance(table_values, list):
        return []
    if not table_values:
        return []

    structured_value = outputs.get("json_sidecar") or outputs.get("structured_json")
    structured_path = _resolve_existing_file(
        manifest_path,
        staging_root,
        structured_value,
        "outputs.json_sidecar",
    )
    if structured_path is None:
        return []

    structured_payload, issues = _read_json_object(structured_path, "docling.json")
    if structured_payload is None:
        return issues

    for value in table_values:
        table_path = _resolve_existing_file(
            manifest_path,
            staging_root,
            value,
            "outputs.table_sidecars",
        )
        if table_path is None:
            continue
        table_payload, table_issues = _read_json_object(table_path, table_path.name)
        issues.extend(table_issues)
        if table_payload is None:
            continue
        issues.extend(
            _validate_table_sidecar_payload(
                table_path,
                table_payload,
                structured_payload,
            )
        )
    return issues


def _validate_table_sidecar_payload(
    table_path: Path,
    payload: dict[str, Any],
    structured_payload: Any,
) -> list[PdfValidationIssue]:
    issues: list[PdfValidationIssue] = []
    if payload.get("schema_version") != 1:
        issues.append(path_issue(table_path, f"{table_path.name} schema_version must be 1"))

    if not isinstance(payload.get("source"), str) or not payload.get("source"):
        issues.append(
            path_issue(table_path, f"{table_path.name} source must be a non-empty string")
        )

    tables = payload.get("tables")
    if not isinstance(tables, list) or not tables:
        issues.append(path_issue(table_path, f"{table_path.name} tables must be a non-empty list"))
        return issues

    for index, table in enumerate(tables):
        if not isinstance(table, dict):
            issues.append(
                path_issue(table_path, f"{table_path.name} tables[{index}] must be an object")
            )
            continue
        table_ref = table.get("path")
        table_payload = table.get("payload")
        if not isinstance(table_ref, str) or not table_ref:
            issues.append(
                path_issue(table_path, f"{table_path.name} tables[{index}].path must be a string")
            )
            continue
        if table_payload in (None, {}, []):
            issues.append(
                path_issue(
                    table_path,
                    f"{table_path.name} tables[{index}].payload must be non-empty",
                )
            )
            continue

        resolved, found = _resolve_json_path(structured_payload, table_ref)
        if not found:
            issues.append(
                path_issue(
                    table_path,
                    f"{table_path.name} table path not found in docling.json: {table_ref}",
                )
            )
        elif resolved != table_payload:
            issues.append(
                path_issue(
                    table_path,
                    f"{table_path.name} table payload does not match docling.json at {table_ref}",
                )
            )
    return issues


def _validate_pdf_markdown_artifact_links(
    manifest_path: Path,
    staging_root: Path,
    outputs: dict[str, Any],
    markdown_path: Path,
) -> list[PdfValidationIssue]:
    issues: list[PdfValidationIssue] = []
    root = _resolve_existing_dir(manifest_path, staging_root, outputs.get("root"), "outputs.root")
    if root is None:
        return issues

    content = markdown_path.read_text(encoding="utf-8")
    linked_targets: set[str] = set()
    for raw_target in MARKDOWN_LINK_RE.findall(content):
        target = _clean_markdown_link_target(raw_target)
        if not _is_pdf_artifact_link_target(target):
            continue
        if _is_unsafe_relative_path(target):
            issues.append(
                path_issue(
                    markdown_path,
                    f"PDF Markdown link escapes artifact directory: {target}",
                )
            )
            continue
        resolved = (markdown_path.parent / target).resolve(strict=False)
        if not resolved.is_relative_to(root):
            issues.append(
                path_issue(
                    markdown_path,
                    f"PDF Markdown link escapes artifact directory: {target}",
                )
            )
            continue
        if not resolved.exists():
            issues.append(
                path_issue(markdown_path, f"PDF Markdown link target does not exist: {target}")
            )
            continue
        linked_targets.add(_markdown_relative_path(markdown_path, resolved))

    expected_files: list[Path] = []
    structured = _resolve_existing_file(
        manifest_path,
        staging_root,
        outputs.get("json_sidecar") or outputs.get("structured_json"),
        "outputs.json_sidecar",
    )
    if structured is not None:
        expected_files.append(structured)

    table_values = outputs.get("table_sidecars") or outputs.get("tables") or []
    if isinstance(table_values, list):
        for value in table_values:
            table_path = _resolve_existing_file(
                manifest_path,
                staging_root,
                value,
                "outputs.table_sidecars",
            )
            if table_path is not None:
                expected_files.append(table_path)

    for expected in expected_files:
        expected_link = _markdown_relative_path(markdown_path, expected)
        if expected_link not in linked_targets:
            issues.append(
                path_issue(
                    markdown_path,
                    f"PDF Markdown does not link artifact: {expected_link}",
                )
            )

    asset_dir_value = outputs.get("asset_dir") or outputs.get("assets_dir")
    if asset_dir_value is not None:
        asset_dir = _resolve_existing_dir(
            manifest_path,
            staging_root,
            asset_dir_value,
            "outputs.asset_dir",
        )
        if asset_dir is not None:
            asset_files = sorted(path for path in asset_dir.rglob("*") if path.is_file())
            if not asset_files:
                issues.append(path_issue(manifest_path, "outputs.asset_dir contains no files"))
            elif not any(
                _markdown_relative_path(markdown_path, asset_file) in linked_targets
                for asset_file in asset_files
            ):
                expected_link = _markdown_relative_path(markdown_path, asset_files[0])
                issues.append(
                    path_issue(
                        markdown_path,
                        f"PDF Markdown does not link asset: {expected_link}",
                    )
                )

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
        "ocr_enabled": (
            "true" if _nested_get(manifest, "extraction", "ocr_enabled") is True else "false"
        ),
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


def _read_json_object(
    path: Path,
    label: str,
) -> tuple[dict[str, Any] | None, list[PdfValidationIssue]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [PdfValidationIssue(path, f"{label} invalid JSON: {exc.msg}")]
    except OSError as exc:
        return None, [PdfValidationIssue(path, f"{label} cannot be read: {exc}")]
    if not isinstance(payload, dict):
        return None, [PdfValidationIssue(path, f"{label} must be a JSON object")]
    return payload, []


def _resolve_existing_file(
    manifest_path: Path,
    staging_root: Path,
    value: Any,
    field_name: str,
) -> Path | None:
    scratch: list[PdfValidationIssue] = []
    resolved = _resolve_optional_output_path(
        manifest_path,
        staging_root,
        value,
        field_name,
        scratch,
    )
    if resolved is None or not resolved.exists() or not resolved.is_file():
        return None
    return resolved


def _resolve_existing_dir(
    manifest_path: Path,
    staging_root: Path,
    value: Any,
    field_name: str,
) -> Path | None:
    scratch: list[PdfValidationIssue] = []
    resolved = _resolve_optional_output_path(
        manifest_path,
        staging_root,
        value,
        field_name,
        scratch,
    )
    if resolved is None or not resolved.exists() or not resolved.is_dir():
        return None
    return resolved


def _resolve_json_path(payload: Any, path: str) -> tuple[Any, bool]:
    if path != "$" and not path.startswith("$.") and not path.startswith("$["):
        return None, False
    current = payload
    index = 1
    while index < len(path):
        marker = path[index]
        if marker == ".":
            index += 1
            start = index
            while index < len(path) and path[index] not in ".[":
                index += 1
            key = path[start:index]
            if not isinstance(current, dict) or key not in current:
                return None, False
            current = current[key]
            continue
        if marker == "[":
            end = path.find("]", index)
            if end == -1:
                return None, False
            raw_index = path[index + 1 : end]
            if not raw_index.isdigit():
                return None, False
            item_index = int(raw_index)
            if not isinstance(current, list) or item_index >= len(current):
                return None, False
            current = current[item_index]
            index = end + 1
            continue
        return None, False
    return current, True


def _clean_markdown_link_target(target: str) -> str:
    return target.split("#", 1)[0].split("?", 1)[0].strip()


def _is_pdf_artifact_link_target(target: str) -> bool:
    normalized = target.replace("\\", "/")
    return (
        normalized.endswith(".json")
        or normalized.startswith("assets/")
        or "/assets/" in normalized
    )


def _markdown_relative_path(markdown_path: Path, target: Path) -> str:
    return (
        target.resolve(strict=False)
        .relative_to(markdown_path.parent.resolve(strict=False))
        .as_posix()
    )


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
    if value.startswith(("/", "\\")):
        return True
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
