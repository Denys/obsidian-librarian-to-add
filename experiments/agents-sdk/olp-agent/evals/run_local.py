from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.graders import assert_path_exists, assert_status  # noqa: E402
from olp_agent.folder_deployment import classify_library_contents, deploy_library_folder, scan_library_folder  # noqa: E402
from olp_agent.safety import ApprovalSet  # noqa: E402
from olp_agent.tools import run_librarian_ingest_draft, run_librarian_search  # noqa: E402


def run_case(case: dict) -> dict:
    case_id = case["id"]
    kind = case["kind"]
    with TemporaryDirectory() as tmp:
        target = Path(tmp) / "library"
        target.mkdir()
        if kind == "deploy_dry_run":
            result = deploy_library_folder(str(target), profile="audiodsp", mode="dry_run")
            assert_status(result.status, "ok", case_id)
            if (target / "90_Staging").exists():
                raise AssertionError(f"{case_id}: dry run wrote infrastructure")
            return {"id": case_id, "status": "pass"}
        if kind == "approved_deploy":
            result = deploy_library_folder(
                str(target),
                profile="audiodsp",
                mode="create_infrastructure",
                approvals=ApprovalSet(approve_create_infrastructure=True),
            )
            assert_status(result.status, "ok", case_id)
            assert_path_exists(target / ".olp_agent" / "deployment.json")
            return {"id": case_id, "status": "pass"}
        if kind == "scan_classify":
            (target / "note.txt").write_text("filter design", encoding="utf-8")
            (target / "paper.pdf").write_bytes(b"%PDF-1.4")
            inventory = scan_library_folder(str(target))
            classified = classify_library_contents(str(target), inventory)
            routes = {item.relative_path: item.route for item in classified.items}
            if routes != {"note.txt": "librarian", "paper.pdf": "patron"}:
                raise AssertionError(f"{case_id}: unexpected routes {routes}")
            return {"id": case_id, "status": "pass"}
        if kind == "missing_write_approval":
            source = target / "note.txt"
            source.write_text("filter design", encoding="utf-8")
            result = run_librarian_ingest_draft(str(source), str(target), approvals=ApprovalSet(), execute=False)
            assert_status(result.status, "needs_approval", case_id)
            if "approve_staging_write" not in result.required_approvals:
                raise AssertionError(f"{case_id}: missing approval flag not reported")
            return {"id": case_id, "status": "pass"}
        if kind == "search_plan":
            result = run_librarian_search(str(target), "filter", execute=False)
            assert_status(result.status, "ok", case_id)
            argv = result.planned_commands[0].argv
            if "--vault" not in argv or str(target) not in argv:
                raise AssertionError(f"{case_id}: explicit vault missing from argv")
            return {"id": case_id, "status": "pass"}
    raise AssertionError(f"Unknown eval case kind: {kind}")


def main() -> int:
    cases_path = ROOT / "evals" / "cases.jsonl"
    results_dir = ROOT / "evals" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    cases = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    results = []
    failures = []
    for case in cases:
        try:
            results.append(run_case(case))
        except Exception as exc:
            failure = {"id": case["id"], "status": "fail", "error": str(exc)}
            failures.append(failure)
            results.append(failure)
    output = {"total": len(cases), "failures": len(failures), "results": results}
    (results_dir / "latest.json").write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
