from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from olp_agent.config import load_config
from olp_agent.schemas import DeploymentResult, IngestWave, InventoryItem, InventoryResult
from olp_agent.safety import ApprovalSet, assert_path_inside, canonical_path, require_approval

INFRA_DIRS = [
    "00_Inbox",
    "10_Knowledge",
    "90_Staging",
    "91_Ingestion",
    ".olp_agent",
    ".olp_agent/runs",
    ".olp_agent/reports",
    ".olp_agent/logs",
]
INFRA_FILES = [
    ".olp_agent/deployment.json",
    ".olp_agent/inventory.json",
    ".olp_agent/ingest_queue.jsonl",
]


def deployment_paths(target_root: Path, profile: str) -> list[Path]:
    paths = [target_root / rel for rel in INFRA_DIRS + INFRA_FILES]
    if profile.lower() == "audiodsp":
        paths.append(target_root / "10_DSP-Eurorack")
    return paths


def deploy_library_folder(
    target_root: str,
    profile: str = "generic",
    mode: str = "dry_run",
    approvals: ApprovalSet | None = None,
) -> DeploymentResult:
    approvals = approvals or ApprovalSet()
    root = canonical_path(target_root)
    if not root.exists():
        return DeploymentResult(
            status="blocked",
            target_root=str(root),
            profile=profile,
            mode=mode,
            summary="Target root does not exist.",
        )
    planned = [str(path) for path in deployment_paths(root, profile)]
    if mode in {"dry_run", "inspect_only"}:
        return DeploymentResult(
            status="ok",
            target_root=str(root),
            profile=profile,
            mode=mode,
            planned_paths=planned,
            writes_performed=False,
            summary="Infrastructure inspection completed without writes.",
        )
    if mode not in {"create_infrastructure", "repair_infrastructure"}:
        return DeploymentResult(
            status="blocked",
            target_root=str(root),
            profile=profile,
            mode=mode,
            planned_paths=planned,
            summary=f"Unsupported deployment mode: {mode}",
        )
    approval = require_approval(["approve_create_infrastructure"], approvals)
    if approval.status != "ok":
        return DeploymentResult(
            status="needs_approval",
            target_root=str(root),
            profile=profile,
            mode=mode,
            planned_paths=planned,
            required_approvals=approval.required_approvals,
            writes_performed=False,
            summary="Creating library infrastructure requires approval.",
        )
    created: list[str] = []
    for rel in INFRA_DIRS:
        path = assert_path_inside(root / rel, [root])
        if not path.exists():
            path.mkdir(parents=True)
            created.append(str(path))
    if profile.lower() == "audiodsp":
        hub = assert_path_inside(root / "10_DSP-Eurorack", [root])
        if not hub.exists():
            hub.mkdir(parents=True)
            created.append(str(hub))
    deployment = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "target_root": str(root),
        "profile": profile,
        "olp_repo_root": str(load_config().olp_repo_root),
        "preferred_staging": "90_Staging",
        "preferred_ingestion": "91_Ingestion",
        "preferred_trusted_hub": "10_DSP-Eurorack" if profile.lower() == "audiodsp" else "10_Knowledge",
        "raw_source_policy": "read_only",
    }
    file_defaults = {
        ".olp_agent/deployment.json": json.dumps(deployment, indent=2, sort_keys=True),
        ".olp_agent/inventory.json": "{}\n",
        ".olp_agent/ingest_queue.jsonl": "",
    }
    for rel, content in file_defaults.items():
        path = assert_path_inside(root / rel, [root])
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(str(path))
    return DeploymentResult(
        status="ok",
        target_root=str(root),
        profile=profile,
        mode=mode,
        planned_paths=planned,
        created_paths=created,
        writes_performed=bool(created),
        summary=f"Created {len(created)} infrastructure paths.",
    )


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _count_summary(items: list[InventoryItem]) -> dict[str, int]:
    summary = {
        "total_files": len(items),
        "pdf": 0,
        "markdown": 0,
        "txt": 0,
        "csv_xlsx": 0,
        "unsupported": 0,
    }
    for item in items:
        suffix = item.suffix.lower()
        if suffix == ".pdf":
            summary["pdf"] += 1
        elif suffix == ".md":
            summary["markdown"] += 1
        elif suffix == ".txt":
            summary["txt"] += 1
        elif suffix in {".csv", ".xlsx", ".xls"}:
            summary["csv_xlsx"] += 1
        else:
            summary["unsupported"] += 1
    return summary


def scan_library_folder(target_root: str) -> InventoryResult:
    root = canonical_path(target_root)
    if not root.exists():
        return InventoryResult(status="blocked", target_root=str(root), summary={"total_files": 0})
    items: list[InventoryItem] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] == ".olp_agent":
            continue
        safe_path = assert_path_inside(path, [root])
        stat = safe_path.stat()
        items.append(
            InventoryItem(
                path=str(safe_path),
                relative_path=str(relative).replace("\\", "/"),
                suffix=safe_path.suffix.lower(),
                size_bytes=stat.st_size,
                modified_time=stat.st_mtime,
                sha256=_hash_file(safe_path),
            )
        )
    return InventoryResult(status="ok", target_root=str(root), items=items, summary=_count_summary(items))


def classify_library_contents(
    target_root: str,
    inventory: InventoryResult | None = None,
) -> InventoryResult:
    inventory = inventory or scan_library_folder(target_root)
    classified: list[InventoryItem] = []
    for item in inventory.items:
        suffix = item.suffix.lower()
        if suffix in {".md", ".txt"}:
            route = "librarian"
            reason = "Text-like source can be staged by obsidian-librarian."
        elif suffix == ".pdf":
            route = "patron"
            reason = "PDF source should use obsidian-patron ingest/propose/link flow."
        elif suffix in {".csv", ".xlsx", ".xls"}:
            route = "manual_review"
            reason = "Spreadsheet conversion is not implemented in current OLP CLI."
        else:
            route = "unsupported"
            reason = "No current OLP route for this suffix."
        classified.append(item.model_copy(update={"route": route, "reason": reason}))
    return InventoryResult(
        status=inventory.status,
        target_root=inventory.target_root,
        items=classified,
        summary=_count_summary(classified),
    )


def plan_ingest_wave(
    target_root: str,
    classified: InventoryResult | None = None,
    max_items: int = 3,
) -> IngestWave:
    classified = classified or classify_library_contents(target_root)
    candidates = [item for item in classified.items if item.route in {"librarian", "patron"}]
    route_priority = {"librarian": 0, "patron": 1}
    candidates.sort(key=lambda item: (route_priority.get(item.route, 9), item.size_bytes, item.relative_path))
    selected = candidates[: max(0, max_items)]
    required: list[str] = []
    if any(item.route == "patron" and item.size_bytes > 10_000_000 for item in selected):
        required.append("approve_large_pdf_ingest")
    return IngestWave(
        status="ok",
        target_root=str(canonical_path(target_root)),
        items=selected,
        required_approvals=required,
        summary=f"Planned {len(selected)} ingest item(s).",
    )
