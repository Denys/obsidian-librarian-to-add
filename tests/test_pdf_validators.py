"""Tests for staged PDF artifact validation."""

from __future__ import annotations

import json
from pathlib import Path

from obsidian_librarian.pdf_validators import validate_pdf_staging_path
from obsidian_librarian.validators import validate_path

HASH = "a" * 64


def make_manifest(
    staging: Path,
    folder: str = "manual",
    *,
    status: str = "staged",
    method: str = "classifier_probe",
    ocr_enabled: bool = False,
    page_count: int = 1,
    source_hash: str = HASH,
    outputs: dict[str, object] | None = None,
) -> Path:
    root = staging / "pdf" / folder
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "source_path": f"{folder}.pdf",
        "source_hash": source_hash,
        "source_kind": "pdf",
        "status": status,
        "page_count": page_count,
        "classification": "digital_pdf",
        "text_density": {
            "total_chars": 100,
            "chars_per_page_min": 100,
            "chars_per_page_median": 100,
            "empty_pages": 0,
        },
        "extraction": {
            "method": method,
            "engine_version": "test",
            "ocr_enabled": ocr_enabled,
            "warnings": [],
        },
        "outputs": outputs if outputs is not None else {"root": f"pdf/{folder}"},
        "provenance": {"page_ranges": []},
    }
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def write_docling_outputs(staging: Path, folder: str = "manual") -> dict[str, object]:
    root = staging / "pdf" / folder
    root.mkdir(parents=True, exist_ok=True)
    (root / "source.md").write_text(
        "---\n"
        "type: \"source\"\n"
        "source_kind: \"pdf\"\n"
        f"source_path: \"{folder}.pdf\"\n"
        f"source_hash: \"{HASH}\"\n"
        "page_count: 1\n"
        "status: \"staged\"\n"
        "confidence: \"source-backed\"\n"
        "extraction_method: \"docling\"\n"
        "ocr_enabled: false\n"
        "---\n\n"
        "# Source\n\n"
        "## Summary\n\nText.\n\n"
        "## Key claims\n\nText.\n\n"
        "## Action items\n\nNone.\n\n"
        "## Open questions\n\nNone.\n\n"
        "## Generated sidecars\n\n"
        "- Structured JSON: [docling.json](docling.json)\n\n"
        "## Links\n\n- Source path.\n",
        encoding="utf-8",
    )
    (root / "docling.json").write_text('{"pages": 1}\n', encoding="utf-8")
    return {
        "root": f"pdf/{folder}",
        "markdown_note": f"pdf/{folder}/source.md",
        "json_sidecar": f"pdf/{folder}/docling.json",
        "table_sidecars": [],
        "asset_dir": None,
    }


def write_ocr_outputs(staging: Path, folder: str = "scan") -> dict[str, object]:
    root = staging / "pdf" / folder
    root.mkdir(parents=True, exist_ok=True)
    (root / "source.md").write_text(
        "---\n"
        "type: \"source\"\n"
        "source_kind: \"pdf\"\n"
        f"source_path: \"{folder}.pdf\"\n"
        f"source_hash: \"{HASH}\"\n"
        "page_count: 1\n"
        "status: \"staged\"\n"
        "review_required: true\n"
        "confidence: \"ocr-derived-needs-review\"\n"
        "extraction_method: \"ocr\"\n"
        "ocr_enabled: true\n"
        "---\n\n"
        "# Source\n\n"
        "## OCR warning\n\nReview against original PDF.\n\n"
        "## Summary\n\nText.\n\n"
        "## Key claims\n\nText.\n\n"
        "## Action items\n\nNone.\n\n"
        "## Open questions\n\nNone.\n\n"
        "## Generated sidecars\n\n"
        "- Structured JSON: [docling.json](docling.json)\n\n"
        "## Links\n\n- Source path.\n",
        encoding="utf-8",
    )
    (root / "docling.json").write_text('{"pages": 1, "ocr": true}\n', encoding="utf-8")
    return {
        "root": f"pdf/{folder}",
        "markdown_note": f"pdf/{folder}/source.md",
        "json_sidecar": f"pdf/{folder}/docling.json",
        "table_sidecars": [],
        "asset_dir": None,
    }


def test_classifier_probe_manifest_requires_only_manifest(tmp_path: Path) -> None:
    staging = tmp_path / "90_Staging"
    make_manifest(staging)

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is True
    assert len(summary.checked_manifests) == 1
    assert summary.issues == []


def test_docling_manifest_requires_markdown_and_json_outputs(tmp_path: Path) -> None:
    staging = tmp_path / "90_Staging"
    outputs = write_docling_outputs(staging)
    make_manifest(staging, method="docling", outputs=outputs)

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is True
    assert len(summary.checked_manifests) == 1


def test_ocr_manifest_accepts_review_required_outputs(tmp_path: Path) -> None:
    staging = tmp_path / "90_Staging"
    outputs = write_ocr_outputs(staging)
    make_manifest(
        staging,
        "scan",
        status="needs_review",
        method="ocr",
        ocr_enabled=True,
        outputs=outputs,
    )

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is True
    assert len(summary.checked_manifests) == 1


def test_ocr_manifest_must_be_review_required(tmp_path: Path) -> None:
    staging = tmp_path / "90_Staging"
    outputs = write_ocr_outputs(staging)
    make_manifest(
        staging,
        "scan",
        status="staged",
        method="ocr",
        ocr_enabled=True,
        outputs=outputs,
    )

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is False
    assert "OCR extraction requires status needs_review" in "\n".join(
        issue.message for issue in summary.issues
    )


def test_docling_manifest_reports_missing_conversion_outputs(tmp_path: Path) -> None:
    staging = tmp_path / "90_Staging"
    make_manifest(
        staging,
        method="docling",
        outputs={
            "root": "pdf/manual",
            "markdown_note": "pdf/manual/source.md",
            "json_sidecar": "pdf/manual/docling.json",
        },
    )

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is False
    messages = "\n".join(issue.message for issue in summary.issues)
    assert "outputs.markdown_note does not exist as a file" in messages
    assert "outputs.json_sidecar does not exist as a file" in messages


def test_output_paths_reject_absolute_and_parent_traversal(tmp_path: Path) -> None:
    staging = tmp_path / "90_Staging"
    make_manifest(
        staging,
        outputs={
            "root": "pdf/manual",
            "markdown_note": "/tmp/outside.md",
            "json_sidecar": "../outside/docling.json",
        },
    )

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is False
    messages = "\n".join(issue.message for issue in summary.issues)
    assert "outputs.markdown_note must stay under 90_Staging" in messages
    assert "outputs.json_sidecar must stay under 90_Staging" in messages


def test_skipped_and_failed_docling_manifests_do_not_require_conversion_outputs(
    tmp_path: Path,
) -> None:
    staging = tmp_path / "90_Staging"
    make_manifest(staging, "scan", status="skipped", method="docling")
    make_manifest(staging, "broken", status="failed", method="docling", page_count=0)

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is True
    assert len(summary.checked_manifests) == 2


def test_claimed_table_sidecars_and_asset_dirs_must_exist(tmp_path: Path) -> None:
    staging = tmp_path / "90_Staging"
    make_manifest(
        staging,
        outputs={
            "root": "pdf/manual",
            "table_sidecars": ["pdf/manual/tables.json"],
            "asset_dir": "pdf/manual/assets",
        },
    )

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is False
    messages = "\n".join(issue.message for issue in summary.issues)
    assert "outputs.table_sidecars item does not exist as a file" in messages
    assert "outputs.asset_dir does not exist as a directory" in messages


def test_existing_asset_dir_is_not_treated_as_separate_pdf_artifact_dir(
    tmp_path: Path,
) -> None:
    staging = tmp_path / "90_Staging"
    asset_dir = staging / "pdf" / "manual" / "assets"
    asset_dir.mkdir(parents=True)
    (asset_dir / "figure.png").write_bytes(b"fake-png")
    make_manifest(
        staging,
        outputs={
            "root": "pdf/manual",
            "asset_dir": "pdf/manual/assets",
        },
    )

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is True
    assert [path.name for path in summary.checked_artifact_dirs] == ["manual"]


def test_pdf_artifact_directory_without_manifest_fails(tmp_path: Path) -> None:
    staging = tmp_path / "90_Staging"
    root = staging / "pdf" / "manual"
    root.mkdir(parents=True)
    (root / "source.md").write_text("# Converted\n", encoding="utf-8")

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is False
    assert "Missing required PDF manifest" in summary.issues[0].message


def test_validate_path_integrates_pdf_artifact_validation(tmp_path: Path) -> None:
    staging = tmp_path / "90_Staging"
    make_manifest(staging, outputs={"root": "pdf/manual", "json_sidecar": "../outside.json"})

    summary = validate_path(staging)

    assert summary.passed is False
    assert len(summary.checked_pdf_manifests) == 1
    assert any("PDF artifact validation" in issue.message for issue in summary.issues)


def test_table_sidecar_payload_must_match_docling_json_path(tmp_path: Path) -> None:
    staging = tmp_path / "90_Staging"
    outputs = write_docling_outputs(staging)
    root = staging / "pdf" / "manual"
    docling_payload = {
        "body": {
            "tables": [
                {"cells": [["Parameter", "Value"], ["Vmax", "600V"]]},
            ],
        },
    }
    table_sidecar = {
        "schema_version": 1,
        "source": "docling_structured_export",
        "tables": [
            {
                "path": "$.body.tables",
                "payload": docling_payload["body"]["tables"],
            },
        ],
    }
    (root / "docling.json").write_text(json.dumps(docling_payload), encoding="utf-8")
    (root / "tables.json").write_text(json.dumps(table_sidecar), encoding="utf-8")
    outputs["table_sidecars"] = ["pdf/manual/tables.json"]
    (root / "source.md").write_text(
        (root / "source.md").read_text(encoding="utf-8")
        .replace(
            "- Structured JSON: [docling.json](docling.json)",
            "- Structured JSON: [docling.json](docling.json)\n"
            "- Tables: [tables.json](tables.json)",
        ),
        encoding="utf-8",
    )
    make_manifest(staging, method="docling", outputs=outputs)

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is True


def test_table_sidecar_payload_mismatch_fails_validation(tmp_path: Path) -> None:
    staging = tmp_path / "90_Staging"
    outputs = write_docling_outputs(staging)
    root = staging / "pdf" / "manual"
    (root / "docling.json").write_text(
        json.dumps({"body": {"tables": [{"cells": [["Parameter"], ["Vmax"]]}]}}),
        encoding="utf-8",
    )
    (root / "tables.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source": "docling_structured_export",
                "tables": [
                    {
                        "path": "$.body.tables",
                        "payload": [{"cells": [["Wrong"], ["Data"]]}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    outputs["table_sidecars"] = ["pdf/manual/tables.json"]
    (root / "source.md").write_text(
        (root / "source.md").read_text(encoding="utf-8")
        .replace(
            "- Structured JSON: [docling.json](docling.json)",
            "- Structured JSON: [docling.json](docling.json)\n"
            "- Tables: [tables.json](tables.json)",
        ),
        encoding="utf-8",
    )
    make_manifest(staging, method="docling", outputs=outputs)

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is False
    messages = "\n".join(issue.message for issue in summary.issues)
    assert "tables.json table payload does not match docling.json at $.body.tables" in messages


def test_malformed_table_sidecar_schema_fails_validation(tmp_path: Path) -> None:
    staging = tmp_path / "90_Staging"
    outputs = write_docling_outputs(staging)
    root = staging / "pdf" / "manual"
    (root / "tables.json").write_text(
        json.dumps({"schema_version": 1, "source": "docling_structured_export", "tables": []}),
        encoding="utf-8",
    )
    outputs["table_sidecars"] = ["pdf/manual/tables.json"]
    (root / "source.md").write_text(
        (root / "source.md").read_text(encoding="utf-8")
        .replace(
            "- Structured JSON: [docling.json](docling.json)",
            "- Structured JSON: [docling.json](docling.json)\n"
            "- Tables: [tables.json](tables.json)",
        ),
        encoding="utf-8",
    )
    make_manifest(staging, method="docling", outputs=outputs)

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is False
    messages = "\n".join(issue.message for issue in summary.issues)
    assert "tables.json tables must be a non-empty list" in messages


def test_pdf_markdown_must_link_manifest_sidecars_and_assets(tmp_path: Path) -> None:
    staging = tmp_path / "90_Staging"
    outputs = write_docling_outputs(staging)
    root = staging / "pdf" / "manual"
    asset_dir = root / "assets"
    asset_dir.mkdir()
    (asset_dir / "page-001-figure-001.png").write_bytes(b"fake-png")
    outputs["asset_dir"] = "pdf/manual/assets"
    make_manifest(staging, method="docling", outputs=outputs)

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is False
    messages = "\n".join(issue.message for issue in summary.issues)
    assert "PDF Markdown does not link asset: assets/page-001-figure-001.png" in messages


def test_pdf_markdown_rejects_sidecar_links_that_escape_artifact_dir(tmp_path: Path) -> None:
    staging = tmp_path / "90_Staging"
    outputs = write_docling_outputs(staging)
    root = staging / "pdf" / "manual"
    (root / "source.md").write_text(
        (root / "source.md").read_text(encoding="utf-8")
        + "\n- Unsafe: [outside](../outside/tables.json)\n",
        encoding="utf-8",
    )
    make_manifest(staging, method="docling", outputs=outputs)

    summary = validate_pdf_staging_path(staging)

    assert summary.passed is False
    messages = "\n".join(issue.message for issue in summary.issues)
    assert "PDF Markdown link escapes artifact directory: ../outside/tables.json" in messages
