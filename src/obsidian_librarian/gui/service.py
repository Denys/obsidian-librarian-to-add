"""Service layer for the local Obsidian Librarian GUI."""

from __future__ import annotations

import contextlib
import io
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from obsidian_inventory import VALID_SCOPES
from obsidian_librarian.cli import main as librarian_main
from obsidian_patron.cli import main as patron_main

READ_ONLY = "read-only"
STAGING_WRITE = "staging-write"
PATRON_INGESTION = "patron-ingestion"
PROMOTION = "promotion"

ParamValue = str | bool | None
Params = Mapping[str, ParamValue]
ArgvBuilder = Callable[[Params], list[str]]


@dataclass(frozen=True)
class ActionParam:
    """Serializable GUI parameter metadata."""

    name: str
    label: str
    kind: str
    required: bool = False
    default: str | bool | None = None
    choices: tuple[str, ...] = ()
    help: str = ""


@dataclass(frozen=True)
class GuiAction:
    """Serializable GUI action metadata."""

    id: str
    label: str
    binary: str
    group: str
    safety_tier: str
    summary: str
    params: tuple[ActionParam, ...] = field(default_factory=tuple)


def _param(
    name: str,
    label: str,
    kind: str,
    *,
    required: bool = False,
    default: str | bool | None = None,
    choices: tuple[str, ...] = (),
    help: str = "",
) -> ActionParam:
    return ActionParam(
        name=name,
        label=label,
        kind=kind,
        required=required,
        default=default,
        choices=choices,
        help=help,
    )


ACTIONS: tuple[GuiAction, ...] = (
    GuiAction(
        id="librarian_ingest",
        label="Stage inbox",
        binary="obsidian-librarian",
        group="Librarian",
        safety_tier=STAGING_WRITE,
        summary="Preview or stage Markdown/TXT inbox files.",
        params=(
            _param("inbox", "Inbox folder", "dir", required=True),
            _param("vault", "Vault root", "vault", required=True, default="."),
            _param(
                "mode",
                "Mode",
                "choice",
                required=True,
                default="read-only",
                choices=("read-only", "draft"),
            ),
            _param("include_pdf", "Include PDFs", "bool", default=False),
            _param(
                "pdf_converter",
                "PDF converter",
                "choice",
                default="none",
                choices=("none", "docling"),
            ),
            _param("pdf_ocr", "Explicit OCR", "bool", default=False),
        ),
    ),
    GuiAction(
        id="librarian_validate",
        label="Validate notes",
        binary="obsidian-librarian",
        group="Librarian",
        safety_tier=READ_ONLY,
        summary="Validate staged Markdown notes.",
        params=(_param("path", "Path", "file", required=True),),
    ),
    GuiAction(
        id="librarian_review_quality",
        label="Review note quality",
        binary="obsidian-librarian",
        group="Librarian",
        safety_tier=READ_ONLY,
        summary="Run deterministic quality checks for staged notes.",
        params=(_param("path", "Path", "file", required=True),),
    ),
    GuiAction(
        id="librarian_index",
        label="Build index",
        binary="obsidian-librarian",
        group="Librarian",
        safety_tier=READ_ONLY,
        summary="Build a deterministic read-only index.",
        params=(
            _param("vault", "Vault root", "vault", required=True, default="."),
            _param("scope", "Scope", "choice", default="vault", choices=VALID_SCOPES),
        ),
    ),
    GuiAction(
        id="librarian_search",
        label="Search vault",
        binary="obsidian-librarian",
        group="Librarian",
        safety_tier=READ_ONLY,
        summary="Search deterministic vault, staging, or ingestion records.",
        params=(
            _param("query", "Query", "query", required=True),
            _param("vault", "Vault root", "vault", required=True, default="."),
            _param("scope", "Scope", "choice", default="vault", choices=VALID_SCOPES),
        ),
    ),
    GuiAction(
        id="librarian_enrich",
        label="Enrich staged notes",
        binary="obsidian-librarian",
        group="Librarian",
        safety_tier=STAGING_WRITE,
        summary="Run deterministic mock or explicit OpenAI enrichment.",
        params=(
            _param("path", "Path", "file", required=True),
            _param("vault", "Vault root", "vault", required=True, default="."),
            _param(
                "mode",
                "Mode",
                "choice",
                default="read-only",
                choices=("read-only", "draft"),
            ),
            _param("extractor", "Extractor", "choice", default="mock", choices=("mock", "openai")),
            _param("model", "Model", "text", default="gpt-5.4-mini"),
        ),
    ),
    GuiAction(
        id="patron_ingest",
        label="Patron PDF ingest",
        binary="obsidian-patron",
        group="Patron",
        safety_tier=PATRON_INGESTION,
        summary="Ingest one engineering PDF into 91_Ingestion.",
        params=(
            _param("pdf", "PDF", "file", required=True),
            _param("vault", "Vault root", "vault", required=True, default="."),
            _param("force", "Force archive previous run", "bool", default=False),
        ),
    ),
    GuiAction(
        id="patron_propose",
        label="Patron proposal",
        binary="obsidian-patron",
        group="Patron",
        safety_tier=PATRON_INGESTION,
        summary="Generate proposal for an ingestion slug.",
        params=(
            _param("slug", "Slug", "slug", required=True),
            _param("vault", "Vault root", "vault", required=True, default="."),
            _param("allow_new_tags", "Allow new tags", "bool", default=False),
            _param("llm", "Explicit LLM", "bool", default=False),
            _param("model", "Model", "text", default="gpt-5.4-mini"),
        ),
    ),
    GuiAction(
        id="patron_link",
        label="Patron link",
        binary="obsidian-patron",
        group="Patron",
        safety_tier=PATRON_INGESTION,
        summary="Insert matched wikilinks and report unmatched candidates.",
        params=(
            _param("slug", "Slug", "slug", required=True),
            _param("vault", "Vault root", "vault", required=True, default="."),
        ),
    ),
    GuiAction(
        id="patron_unmatched",
        label="Patron unmatched",
        binary="obsidian-patron",
        group="Patron",
        safety_tier=READ_ONLY,
        summary="Print unmatched candidates report.",
        params=(
            _param("slug", "Slug", "slug", required=True),
            _param("vault", "Vault root", "vault", required=True, default="."),
        ),
    ),
    GuiAction(
        id="patron_status",
        label="Patron status",
        binary="obsidian-patron",
        group="Patron",
        safety_tier=READ_ONLY,
        summary="Show current location and provenance for a slug.",
        params=(
            _param("slug", "Slug", "slug", required=True),
            _param("vault", "Vault root", "vault", required=True, default="."),
        ),
    ),
    GuiAction(
        id="patron_promote",
        label="Patron promote",
        binary="obsidian-patron",
        group="Patron",
        safety_tier=PROMOTION,
        summary="Promote an ingestion slug to staging or a trusted hub.",
        params=(
            _param("slug", "Slug", "slug", required=True),
            _param("vault", "Vault root", "vault", required=True, default="."),
            _param("target", "Target", "choice", default="staging", choices=("staging", "trusted")),
            _param("hub", "Trusted hub", "text"),
            _param("override", "Override existing trusted note", "bool", default=False),
        ),
    ),
    GuiAction(
        id="patron_unpromote",
        label="Patron unpromote",
        binary="obsidian-patron",
        group="Patron",
        safety_tier=PROMOTION,
        summary="Reverse a recorded promotion.",
        params=(
            _param("slug", "Slug", "slug", required=True),
            _param("vault", "Vault root", "vault", required=True, default="."),
        ),
    ),
)

ACTION_BY_ID = {action.id: action for action in ACTIONS}


def _str_param(params: Params, name: str) -> str:
    value = params.get(name)
    if value is None:
        return ""
    return str(value)


def _bool_param(params: Params, name: str) -> bool:
    return bool(params.get(name))


def _ingest_argv(params: Params) -> list[str]:
    argv = [
        "ingest",
        _str_param(params, "inbox"),
        "--vault",
        _str_param(params, "vault") or ".",
        "--mode",
        _str_param(params, "mode") or "read-only",
    ]
    if _bool_param(params, "include_pdf"):
        argv.append("--include-pdf")
    converter = _str_param(params, "pdf_converter") or "none"
    if converter != "none":
        argv.extend(["--pdf-converter", converter])
    if _bool_param(params, "pdf_ocr"):
        argv.append("--pdf-ocr")
    return argv


def _enrich_argv(params: Params) -> list[str]:
    extractor = _str_param(params, "extractor") or "mock"
    argv = [
        "enrich",
        _str_param(params, "path"),
        "--vault",
        _str_param(params, "vault") or ".",
        "--mode",
        _str_param(params, "mode") or "read-only",
        "--extractor",
        extractor,
    ]
    model = _str_param(params, "model")
    if model:
        argv.extend(["--model", model])
    return argv


def _patron_promote_argv(params: Params) -> list[str]:
    target = _str_param(params, "target") or "staging"
    argv = ["promote", _str_param(params, "slug"), "--vault", _str_param(params, "vault") or "."]
    if target == "staging":
        argv.append("--to-staging")
    elif target == "trusted":
        hub = _str_param(params, "hub")
        if not hub:
            raise ValueError("--hub is required when target is trusted")
        argv.extend(["--to-trusted", "--hub", hub])
    else:
        raise ValueError(f"Unsupported Patron promotion target: {target}")
    if _bool_param(params, "override"):
        argv.append("--override")
    return argv


def _patron_ingest_argv(params: Params) -> list[str]:
    argv = ["ingest", _str_param(params, "pdf"), "--vault", _str_param(params, "vault") or "."]
    if _bool_param(params, "force"):
        argv.append("--force")
    return argv


def _patron_propose_argv(params: Params) -> list[str]:
    argv = ["propose", _str_param(params, "slug"), "--vault", _str_param(params, "vault") or "."]
    if _bool_param(params, "allow_new_tags"):
        argv.append("--allow-new-tags")
    if _bool_param(params, "llm"):
        argv.append("--llm")
    argv.extend(["--model", _str_param(params, "model") or "gpt-5.4-mini"])
    return argv


ARGV_BUILDERS: dict[str, ArgvBuilder] = {
    "librarian_ingest": _ingest_argv,
    "librarian_validate": lambda p: ["validate", _str_param(p, "path")],
    "librarian_review_quality": lambda p: ["review-quality", _str_param(p, "path")],
    "librarian_index": lambda p: [
        "index",
        "--vault",
        _str_param(p, "vault") or ".",
        "--scope",
        _str_param(p, "scope") or "vault",
    ],
    "librarian_search": lambda p: [
        "search",
        _str_param(p, "query"),
        "--vault",
        _str_param(p, "vault") or ".",
        "--scope",
        _str_param(p, "scope") or "vault",
    ],
    "librarian_enrich": _enrich_argv,
    "patron_ingest": _patron_ingest_argv,
    "patron_propose": _patron_propose_argv,
    "patron_link": lambda p: [
        "link",
        _str_param(p, "slug"),
        "--vault",
        _str_param(p, "vault") or ".",
    ],
    "patron_unmatched": lambda p: [
        "unmatched",
        _str_param(p, "slug"),
        "--vault",
        _str_param(p, "vault") or ".",
    ],
    "patron_status": lambda p: [
        "status",
        _str_param(p, "slug"),
        "--vault",
        _str_param(p, "vault") or ".",
    ],
    "patron_promote": _patron_promote_argv,
    "patron_unpromote": lambda p: [
        "unpromote",
        _str_param(p, "slug"),
        "--vault",
        _str_param(p, "vault") or ".",
    ],
}


def action_registry() -> list[dict[str, Any]]:
    """Return JSON-serializable metadata for all GUI actions."""
    return [asdict(action) for action in ACTIONS]


def get_action(action_id: str) -> GuiAction:
    """Return action metadata or raise a stable error."""
    try:
        return ACTION_BY_ID[action_id]
    except KeyError as exc:
        raise ValueError(f"Unknown GUI action: {action_id}") from exc


def _merged_params(action: GuiAction, params: Params) -> dict[str, ParamValue]:
    merged: dict[str, ParamValue] = {param.name: param.default for param in action.params}
    merged.update(params)
    return merged


def validate_required_params(action: GuiAction, params: Params) -> None:
    """Validate required GUI params before invoking argparse."""
    for param in action.params:
        value = params.get(param.name, param.default)
        if param.required and (value is None or str(value).strip() == ""):
            raise ValueError(f"Missing required parameter: {param.name}")


def build_action_argv(action_id: str, params: Params) -> list[str]:
    """Build the CLI argv list for a GUI action."""
    action = get_action(action_id)
    merged = _merged_params(action, params)
    validate_required_params(action, merged)
    return ARGV_BUILDERS[action_id](merged)


def effective_tier(action_id: str, params: Params) -> str:
    """Return the action safety tier after dynamic mode choices."""
    action = get_action(action_id)
    if action_id in {"librarian_ingest", "librarian_enrich"}:
        mode = _str_param(params, "mode") or "read-only"
        return READ_ONLY if mode == "read-only" else STAGING_WRITE
    return action.safety_tier


def equivalent_cli(action: GuiAction, argv: list[str]) -> str:
    """Return a copyable command line for the GUI preview."""
    return subprocess.list2cmdline([action.binary, *argv])


def run_action(action_id: str, params: Params, *, confirmed: bool = False) -> dict[str, Any]:
    """Run one GUI action through the existing CLI boundary."""
    try:
        action = get_action(action_id)
        merged = _merged_params(action, params)
        argv = build_action_argv(action_id, merged)
        tier = effective_tier(action_id, merged)
        command = equivalent_cli(action, argv)
    except ValueError as exc:
        return {
            "status": "error",
            "executed": False,
            "exit_code": 2,
            "safety_tier": "unknown",
            "equivalent_cli": "",
            "stdout": "",
            "stderr": "",
            "output": f"Error: {exc}",
        }

    if tier != READ_ONLY and not confirmed:
        return {
            "status": "needs_confirmation",
            "executed": False,
            "exit_code": None,
            "safety_tier": tier,
            "equivalent_cli": command,
            "stdout": "",
            "stderr": "",
            "output": "",
        }

    stdout = io.StringIO()
    stderr = io.StringIO()
    main_func = librarian_main if action.binary == "obsidian-librarian" else patron_main
    exit_code = 1
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            exit_code = main_func(argv)
        except SystemExit as exc:
            exit_code = int(exc.code) if isinstance(exc.code, int) else 1
        except Exception as exc:  # noqa: BLE001 - GUI must report unexpected CLI adapter errors.
            print(f"Error: {exc}")
            exit_code = 1

    out = stdout.getvalue()
    err = stderr.getvalue()
    return {
        "status": "ok" if exit_code == 0 else "error",
        "executed": True,
        "exit_code": exit_code,
        "safety_tier": tier,
        "equivalent_cli": command,
        "stdout": out,
        "stderr": err,
        "output": out if not err else f"{out}\n{err}".strip(),
    }


def browse_directory(path: str | None = None) -> dict[str, Any]:
    """Return local directory entries for the server-side picker."""
    root = Path(path or Path.home()).expanduser().resolve(strict=False)
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {root}")
    if not root.is_dir():
        root = root.parent

    entries = []
    for child in sorted(root.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower())):
        entries.append(
            {
                "name": child.name,
                "path": str(child.resolve(strict=False)),
                "is_dir": child.is_dir(),
            }
        )

    parent = root.parent if root.parent != root else root
    return {
        "path": str(root.resolve(strict=False)),
        "parent": str(parent.resolve(strict=False)),
        "entries": entries,
    }


def save_pasted_source(text: str, kind: str = "md") -> dict[str, str]:
    """Persist pasted text to a temp inbox file and return provenance."""
    if not text:
        raise ValueError("Pasted text must not be empty")
    suffix = ".txt" if kind == "txt" else ".md"
    inbox_dir = Path(tempfile.mkdtemp(prefix="obsidian-librarian-paste-"))
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    file_path = inbox_dir / f"pasted-{timestamp}{suffix}"
    file_path.write_text(text, encoding="utf-8")
    return {
        "inbox_dir": str(inbox_dir),
        "file_path": str(file_path),
        "provenance": f"pasted source saved at {timestamp}",
    }
