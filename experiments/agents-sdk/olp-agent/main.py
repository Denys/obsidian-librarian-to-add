from __future__ import annotations

import argparse
import json
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from olp_agent.agent import run_agent_request
from olp_agent.config import health, load_config
from olp_agent.folder_deployment import (
    classify_library_contents,
    deploy_library_folder,
    plan_ingest_wave,
    scan_library_folder,
)
from olp_agent.safety import ApprovalSet

app = FastAPI(title="OLP Agents SDK Agent")


class RunRequest(BaseModel):
    request: str


def _json(data: Any) -> str:
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    return json.dumps(data, indent=2, sort_keys=True)


@app.get("/health")
def http_health() -> dict:
    return health().model_dump()


@app.post("/run")
async def http_run(payload: RunRequest, x_olp_run_token: str | None = Header(default=None)) -> dict:
    cfg = load_config()
    if cfg.run_token and x_olp_run_token != cfg.run_token:
        raise HTTPException(status_code=401, detail="Invalid OLP run token")
    result = await run_agent_request(payload.request)
    return result.model_dump()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone OLP Agents SDK agent.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="Print health/readiness JSON.")

    deploy = sub.add_parser("deploy-library", help="Inspect or create OLP target infrastructure.")
    deploy.add_argument("--target", required=True)
    deploy.add_argument("--profile", default="generic")
    deploy.add_argument("--dry-run", action="store_true")
    deploy.add_argument("--mode", choices=["dry_run", "inspect_only", "create_infrastructure", "repair_infrastructure"])
    deploy.add_argument("--approve-create-infrastructure", action="store_true")

    scan = sub.add_parser("scan-library", help="Read-only inventory of target folder.")
    scan.add_argument("--target", required=True)

    classify = sub.add_parser("classify-library", help="Classify target folder inventory.")
    classify.add_argument("--target", required=True)

    wave = sub.add_parser("plan-wave", help="Plan the next small ingest wave.")
    wave.add_argument("--target", required=True)
    wave.add_argument("--max-items", type=int, default=3)

    run = sub.add_parser("run", help="Run the live Agents SDK path.")
    run.add_argument("request")

    serve = sub.add_parser("serve", help="Start the localhost HTTP service.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "health":
        print(_json(health()))
        return 0
    if args.command == "deploy-library":
        mode = args.mode or ("dry_run" if args.dry_run else "inspect_only")
        result = deploy_library_folder(
            target_root=args.target,
            profile=args.profile,
            mode=mode,
            approvals=ApprovalSet(
                approve_create_infrastructure=args.approve_create_infrastructure
            ),
        )
        print(_json(result))
        return 0 if result.status == "ok" else 2
    if args.command == "scan-library":
        print(_json(scan_library_folder(args.target)))
        return 0
    if args.command == "classify-library":
        print(_json(classify_library_contents(args.target)))
        return 0
    if args.command == "plan-wave":
        classified = classify_library_contents(args.target)
        print(_json(plan_ingest_wave(args.target, classified, max_items=args.max_items)))
        return 0
    if args.command == "run":
        from olp_agent.agent import run_agent_request_sync

        result = run_agent_request_sync(args.request)
        print(_json(result))
        return 0 if result.status in {"ok", "needs_approval", "blocked"} else 2
    if args.command == "serve":
        import uvicorn

        cfg = load_config()
        uvicorn.run("main:app", host=args.host, port=args.port or cfg.port)
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
