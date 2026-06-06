from __future__ import annotations

import json
import os
import subprocess

from olp_agent.command_runner import run_command
from olp_agent.config import health, load_config
from olp_agent.folder_deployment import (
    classify_library_contents,
    deploy_library_folder,
    plan_ingest_wave,
    scan_library_folder,
)
from olp_agent.schemas import Artifact, PlannedCommand, ToolResult
from olp_agent.safety import ApprovalSet, assert_path_inside, canonical_path, require_approval


def resolve_olp_environment() -> dict:
    return health().model_dump()


def _base_command(module: str) -> list[str]:
    cfg = load_config()
    return [str(cfg.olp_python), "-m", module]


def _run_or_plan(
    *,
    label: str,
    argv: list[str],
    workflow: str,
    safety_tier: str,
    execute: bool,
    summary: str,
) -> ToolResult:
    planned = PlannedCommand(label=label, argv=argv, requires_approval=False)
    if not execute:
        return ToolResult(
            status="ok",
            workflow=workflow,  # type: ignore[arg-type]
            safety_tier=safety_tier,  # type: ignore[arg-type]
            summary=summary,
            planned_commands=[planned],
        )
    cfg = load_config()
    executed = run_command(label=label, argv=argv, cwd=cfg.olp_repo_root)
    status = "ok" if executed.exit_code == 0 and not executed.timed_out else "error"
    text = executed.stdout + "\n" + executed.stderr
    if "std::bad_alloc" in text or "failed" in text.lower() or "traceback" in text.lower():
        status = "needs_review" if executed.exit_code == 0 else "error"
    return ToolResult(
        status=status,  # type: ignore[arg-type]
        workflow=workflow,  # type: ignore[arg-type]
        safety_tier=safety_tier,  # type: ignore[arg-type]
        summary=summary,
        planned_commands=[planned],
        executed_commands=[executed],
    )


def _approval_result(
    required: list[str],
    approvals: ApprovalSet,
    *,
    workflow: str,
    safety_tier: str,
    summary: str,
    planned: PlannedCommand | None = None,
) -> ToolResult | None:
    outcome = require_approval(required, approvals)
    if outcome.status == "ok":
        return None
    if planned is not None:
        planned.requires_approval = True
        planned.required_approvals = outcome.required_approvals
    return ToolResult(
        status="needs_approval",
        workflow=workflow,  # type: ignore[arg-type]
        safety_tier=safety_tier,  # type: ignore[arg-type]
        required_approvals=outcome.required_approvals,
        planned_commands=[planned] if planned else [],
        summary=summary,
    )


def deploy_library_folder_tool(
    target_root: str,
    profile: str = "generic",
    mode: str = "dry_run",
    approvals: ApprovalSet | None = None,
) -> dict:
    return deploy_library_folder(target_root, profile, mode, approvals or ApprovalSet()).model_dump()


def scan_library_folder_tool(target_root: str) -> dict:
    return scan_library_folder(target_root).model_dump()


def classify_library_contents_tool(target_root: str) -> dict:
    return classify_library_contents(target_root).model_dump()


def plan_ingest_wave_tool(target_root: str, max_items: int = 3) -> dict:
    classified = classify_library_contents(target_root)
    return plan_ingest_wave(target_root, classified, max_items=max_items).model_dump()


def run_librarian_ingest_preview(
    source_path: str,
    vault_root: str,
    approvals: ApprovalSet | None = None,
    include_pdf: bool = False,
    include_pdf_ocr: bool = False,
    execute: bool = False,
) -> ToolResult:
    approvals = approvals or ApprovalSet()
    required = ["approve_ocr"] if include_pdf_ocr else []
    source = canonical_path(source_path)
    vault = canonical_path(vault_root)
    if not source.exists() or not vault.exists():
        return ToolResult(status="blocked", workflow="librarian", summary="Source or vault path missing.")
    assert_path_inside(vault, [vault])
    argv = _base_command("obsidian_librarian.cli") + [
        "ingest",
        str(source),
        "--vault",
        str(vault),
        "--mode",
        "read-only",
    ]
    if include_pdf:
        argv.append("--include-pdf")
    if include_pdf_ocr:
        argv.append("--pdf-ocr")
    planned = PlannedCommand(label="librarian ingest preview", argv=argv, requires_approval=bool(required))
    approval_result = _approval_result(
        required,
        approvals,
        workflow="librarian",
        safety_tier="opt_in_ocr_or_llm" if include_pdf_ocr else "read_only",
        summary="Read-only ingest preview needs OCR approval.",
        planned=planned,
    )
    if approval_result:
        return approval_result
    return _run_or_plan(
        label="librarian ingest preview",
        argv=argv,
        workflow="librarian",
        safety_tier="opt_in_ocr_or_llm" if include_pdf_ocr else "read_only",
        execute=execute,
        summary="Planned librarian read-only ingest preview.",
    )


def run_librarian_ingest_draft(
    source_path: str,
    vault_root: str,
    approvals: ApprovalSet | None = None,
    include_pdf: bool = False,
    include_pdf_ocr: bool = False,
    execute: bool = False,
) -> ToolResult:
    approvals = approvals or ApprovalSet()
    required = ["approve_staging_write"]
    if include_pdf_ocr:
        required.append("approve_ocr")
    source = canonical_path(source_path)
    vault = canonical_path(vault_root)
    argv = _base_command("obsidian_librarian.cli") + [
        "ingest",
        str(source),
        "--vault",
        str(vault),
        "--mode",
        "draft",
    ]
    if include_pdf:
        argv.append("--include-pdf")
    if include_pdf_ocr:
        argv.append("--pdf-ocr")
    planned = PlannedCommand(label="librarian ingest draft", argv=argv, requires_approval=True)
    approval_result = _approval_result(
        required,
        approvals,
        workflow="librarian",
        safety_tier="staging_write",
        summary="Draft ingest writes to staging and needs approval.",
        planned=planned,
    )
    if approval_result:
        return approval_result
    return _run_or_plan(
        label="librarian ingest draft",
        argv=argv,
        workflow="librarian",
        safety_tier="staging_write",
        execute=execute,
        summary="Planned approved librarian draft ingest.",
    )


def run_librarian_validate(vault_root: str, execute: bool = True) -> ToolResult:
    vault = canonical_path(vault_root)
    argv = _base_command("obsidian_librarian.cli") + ["validate", "--vault", str(vault)]
    return _run_or_plan(
        label="librarian validate",
        argv=argv,
        workflow="librarian",
        safety_tier="read_only",
        execute=execute,
        summary="Validate staged Markdown notes.",
    )


def run_librarian_review_quality(vault_root: str, execute: bool = True) -> ToolResult:
    vault = canonical_path(vault_root)
    argv = _base_command("obsidian_librarian.cli") + ["review-quality", "--vault", str(vault)]
    return _run_or_plan(
        label="librarian review-quality",
        argv=argv,
        workflow="librarian",
        safety_tier="read_only",
        execute=execute,
        summary="Review staged note quality.",
    )


def run_librarian_enrich(
    path: str,
    vault_root: str,
    approvals: ApprovalSet | None = None,
    mode: str = "read-only",
    extractor: str = "mock",
    model: str = "gpt-5.4-mini",
    execute: bool = False,
) -> ToolResult:
    approvals = approvals or ApprovalSet()
    required: list[str] = []
    if mode == "draft":
        required.append("approve_staging_write")
    if extractor == "openai":
        required.append("approve_llm")
    target = canonical_path(path)
    vault = canonical_path(vault_root)
    argv = _base_command("obsidian_librarian.cli") + [
        "enrich",
        str(target),
        "--vault",
        str(vault),
        "--mode",
        mode,
        "--extractor",
        extractor,
        "--model",
        model,
    ]
    planned = PlannedCommand(label="librarian enrich", argv=argv, requires_approval=bool(required))
    approval_result = _approval_result(
        required,
        approvals,
        workflow="librarian",
        safety_tier="opt_in_ocr_or_llm" if extractor == "openai" else "staging_write",
        summary="Enrichment needs the requested approvals.",
        planned=planned,
    )
    if approval_result:
        return approval_result
    return _run_or_plan(
        label="librarian enrich",
        argv=argv,
        workflow="librarian",
        safety_tier="opt_in_ocr_or_llm" if extractor == "openai" else "read_only",
        execute=execute,
        summary="Planned librarian enrichment.",
    )


def run_librarian_index(vault_root: str, scope: str = "vault-and-staging", execute: bool = False) -> ToolResult:
    vault = canonical_path(vault_root)
    argv = _base_command("obsidian_librarian.cli") + [
        "index",
        "--vault",
        str(vault),
        "--scope",
        scope,
    ]
    return _run_or_plan(
        label="librarian index",
        argv=argv,
        workflow="librarian",
        safety_tier="read_only",
        execute=execute,
        summary="Build deterministic OLP index.",
    )


def run_librarian_search(
    vault_root: str,
    query: str,
    approvals: ApprovalSet | None = None,
    scope: str = "vault-and-staging",
    execute: bool = False,
) -> ToolResult:
    _ = approvals or ApprovalSet()
    vault = canonical_path(vault_root)
    argv = _base_command("obsidian_librarian.cli") + [
        "search",
        query,
        "--vault",
        str(vault),
        "--scope",
        scope,
    ]
    return _run_or_plan(
        label="librarian search",
        argv=argv,
        workflow="librarian",
        safety_tier="read_only",
        execute=execute,
        summary="Search deterministic OLP index.",
    )


def run_librarian_report(vault_root: str, execute: bool = False) -> ToolResult:
    vault = canonical_path(vault_root)
    argv = _base_command("obsidian_librarian.cli") + ["report", "--vault", str(vault)]
    if not execute:
        return ToolResult(
            status="unavailable",
            workflow="librarian",
            safety_tier="read_only",
            planned_commands=[PlannedCommand(label="librarian report", argv=argv)],
            summary="Librarian report is currently a placeholder in OLP.",
        )
    return _run_or_plan(
        label="librarian report",
        argv=argv,
        workflow="librarian",
        safety_tier="read_only",
        execute=True,
        summary="Ran stub-aware librarian report.",
    )


def launch_librarian_gui(
    vault_root: str,
    approvals: ApprovalSet | None = None,
    host: str = "127.0.0.1",
    port: int = 0,
    execute: bool = False,
) -> ToolResult:
    approvals = approvals or ApprovalSet()
    if host != "127.0.0.1":
        return ToolResult(
            status="blocked",
            workflow="librarian",
            safety_tier="gui_launch",
            summary="GUI launch only allows 127.0.0.1 in this agent version.",
        )
    vault = canonical_path(vault_root)
    argv = _base_command("obsidian_librarian.cli") + [
        "gui",
        "--vault",
        str(vault),
        "--host",
        host,
        "--port",
        str(port),
    ]
    planned = PlannedCommand(label="librarian gui", argv=argv, requires_approval=True)
    approval_result = _approval_result(
        ["approve_launch_gui"],
        approvals,
        workflow="librarian",
        safety_tier="gui_launch",
        summary="Launching the GUI requires approval.",
        planned=planned,
    )
    if approval_result:
        return approval_result
    if not execute:
        return ToolResult(
            status="ok",
            workflow="librarian",
            safety_tier="gui_launch",
            summary="Planned approved GUI launch.",
            planned_commands=[planned],
        )
    cfg = load_config()
    process = subprocess.Popen(argv, cwd=str(cfg.olp_repo_root))  # noqa: S603
    return ToolResult(
        status="ok",
        workflow="librarian",
        safety_tier="gui_launch",
        summary=f"Started GUI process {process.pid}.",
        planned_commands=[planned],
        artifacts=[
            Artifact(
                kind="process",
                path=str(process.pid),
                description=f"GUI requested at http://{host}:{port or '<auto>'}",
            )
        ],
    )


def run_patron_ingest(
    pdf_path: str,
    vault_root: str,
    approvals: ApprovalSet | None = None,
    force: bool = False,
    execute: bool = False,
) -> ToolResult:
    approvals = approvals or ApprovalSet()
    pdf = canonical_path(pdf_path)
    vault = canonical_path(vault_root)
    required = ["approve_staging_write"]
    if force:
        required.append("approve_force_overwrite")
    if pdf.exists() and pdf.stat().st_size > 10_000_000:
        required.append("approve_large_pdf_ingest")
    argv = _base_command("obsidian_patron.cli") + ["ingest", str(pdf), "--vault", str(vault)]
    if force:
        argv.append("--force")
    planned = PlannedCommand(label="patron ingest", argv=argv, requires_approval=True)
    approval_result = _approval_result(
        required,
        approvals,
        workflow="patron",
        safety_tier="force_overwrite" if force else "staging_write",
        summary="Patron PDF ingest writes under 91_Ingestion and needs approval.",
        planned=planned,
    )
    if approval_result:
        return approval_result
    return _run_or_plan(
        label="patron ingest",
        argv=argv,
        workflow="patron",
        safety_tier="force_overwrite" if force else "staging_write",
        execute=execute,
        summary="Planned approved Patron ingest.",
    )


def run_patron_propose(
    slug: str,
    vault_root: str,
    approvals: ApprovalSet | None = None,
    allow_new_tags: bool = False,
    llm: bool = False,
    model: str = "gpt-5.4-mini",
    execute: bool = False,
) -> ToolResult:
    approvals = approvals or ApprovalSet()
    vault = canonical_path(vault_root)
    required = ["approve_staging_write"]
    if llm:
        required.append("approve_llm")
    argv = _base_command("obsidian_patron.cli") + ["propose", slug, "--vault", str(vault)]
    if allow_new_tags:
        argv.append("--allow-new-tags")
    if llm:
        argv.extend(["--llm", "--model", model])
    planned = PlannedCommand(label="patron propose", argv=argv, requires_approval=True)
    approval_result = _approval_result(
        required,
        approvals,
        workflow="patron",
        safety_tier="opt_in_ocr_or_llm" if llm else "staging_write",
        summary="Patron propose writes _proposal.md and needs approval.",
        planned=planned,
    )
    if approval_result:
        return approval_result
    return _run_or_plan(
        label="patron propose",
        argv=argv,
        workflow="patron",
        safety_tier="opt_in_ocr_or_llm" if llm else "staging_write",
        execute=execute,
        summary="Planned approved Patron proposal.",
    )


def run_patron_link(
    slug: str,
    vault_root: str,
    approvals: ApprovalSet | None = None,
    execute: bool = False,
) -> ToolResult:
    approvals = approvals or ApprovalSet()
    vault = canonical_path(vault_root)
    argv = _base_command("obsidian_patron.cli") + ["link", slug, "--vault", str(vault)]
    planned = PlannedCommand(label="patron link", argv=argv, requires_approval=True)
    approval_result = _approval_result(
        ["approve_staging_write"],
        approvals,
        workflow="patron",
        safety_tier="staging_write",
        summary="Patron link writes notes and unmatched report.",
        planned=planned,
    )
    if approval_result:
        return approval_result
    return _run_or_plan(
        label="patron link",
        argv=argv,
        workflow="patron",
        safety_tier="staging_write",
        execute=execute,
        summary="Planned approved Patron link.",
    )


def run_patron_unmatched(slug: str, vault_root: str, execute: bool = False) -> ToolResult:
    vault = canonical_path(vault_root)
    argv = _base_command("obsidian_patron.cli") + ["unmatched", slug, "--vault", str(vault)]
    return _run_or_plan(
        label="patron unmatched",
        argv=argv,
        workflow="patron",
        safety_tier="read_only",
        execute=execute,
        summary="Read Patron unmatched report.",
    )


def run_patron_status(slug: str, vault_root: str, execute: bool = False) -> ToolResult:
    vault = canonical_path(vault_root)
    argv = _base_command("obsidian_patron.cli") + ["status", slug, "--vault", str(vault)]
    return _run_or_plan(
        label="patron status",
        argv=argv,
        workflow="patron",
        safety_tier="read_only",
        execute=execute,
        summary="Read Patron slug status.",
    )


def run_patron_promote(
    slug: str,
    vault_root: str,
    approvals: ApprovalSet | None = None,
    destination: str = "staging",
    hub: str | None = None,
    override: bool = False,
    execute: bool = False,
) -> ToolResult:
    approvals = approvals or ApprovalSet()
    vault = canonical_path(vault_root)
    argv = _base_command("obsidian_patron.cli") + ["promote", slug, "--vault", str(vault)]
    if destination == "trusted":
        if not hub:
            return ToolResult(
                status="blocked",
                workflow="patron",
                safety_tier="promotion",
                summary="Trusted promotion requires explicit hub.",
            )
        argv.extend(["--to-trusted", "--hub", hub])
    else:
        argv.append("--to-staging")
    if override:
        argv.append("--override")
    planned = PlannedCommand(label="patron promote", argv=argv, requires_approval=True)
    approval_result = _approval_result(
        ["approve_promotion"],
        approvals,
        workflow="patron",
        safety_tier="promotion",
        summary="Promotion requires approval.",
        planned=planned,
    )
    if approval_result:
        return approval_result
    return _run_or_plan(
        label="patron promote",
        argv=argv,
        workflow="patron",
        safety_tier="promotion",
        execute=execute,
        summary="Planned approved Patron promotion.",
    )


def run_patron_unpromote(
    slug: str,
    vault_root: str,
    approvals: ApprovalSet | None = None,
    execute: bool = False,
) -> ToolResult:
    approvals = approvals or ApprovalSet()
    vault = canonical_path(vault_root)
    argv = _base_command("obsidian_patron.cli") + ["unpromote", slug, "--vault", str(vault)]
    planned = PlannedCommand(label="patron unpromote", argv=argv, requires_approval=True)
    approval_result = _approval_result(
        ["approve_unpromotion"],
        approvals,
        workflow="patron",
        safety_tier="promotion",
        summary="Unpromotion requires explicit approval.",
        planned=planned,
    )
    if approval_result:
        return approval_result
    return _run_or_plan(
        label="patron unpromote",
        argv=argv,
        workflow="patron",
        safety_tier="promotion",
        execute=execute,
        summary="Planned approved Patron unpromotion.",
    )


def read_agent_state(target_root: str) -> dict:
    root = canonical_path(target_root)
    state_dir = root / ".olp_agent"
    data: dict[str, object] = {}
    for name in ["deployment.json", "inventory.json"]:
        path = state_dir / name
        if path.exists():
            data[name] = json.loads(path.read_text(encoding="utf-8"))
    queue = state_dir / "ingest_queue.jsonl"
    if queue.exists():
        data["ingest_queue.jsonl"] = queue.read_text(encoding="utf-8").splitlines()
    return data


def read_olp_artifact(path: str, target_root: str, max_bytes: int = 4000) -> dict:
    root = canonical_path(target_root)
    artifact = assert_path_inside(path, [root])
    if not artifact.exists() or not artifact.is_file():
        return {"status": "blocked", "summary": "Artifact path missing or not a file."}
    return {
        "status": "ok",
        "path": str(artifact),
        "text": artifact.read_bytes()[:max_bytes].decode("utf-8", errors="replace"),
    }


def openai_key_present() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))
