from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

try:
    import agents  # type: ignore
except Exception:  # pragma: no cover - depends on optional install state
    agents = None

from pydantic import BaseModel

from olp_agent.schemas import HealthResult

DEFAULT_OLP_REPO_ROOT = Path(r"C:\Users\denko\Codex\obsidian-librarian-to-add")
DEFAULT_TARGET_LIBRARY = Path(r"C:\Users\denko\Codex2\AudioDSP_example_library")


class AppConfig(BaseModel):
    olp_repo_root: Path
    olp_python: Path
    target_library: Path | None = None
    agent_model: str = "gpt-5.4-mini"
    port: int = 8421
    run_token: str = ""


def _env_path(name: str, default: Path | None = None) -> Path | None:
    value = os.getenv(name)
    if value:
        return Path(value)
    return default


def load_config() -> AppConfig:
    repo_root = _env_path("OLP_REPO_ROOT", DEFAULT_OLP_REPO_ROOT) or DEFAULT_OLP_REPO_ROOT
    configured_python = _env_path("OLP_PYTHON")
    default_venv = repo_root / ".venv314" / "Scripts" / "python.exe"
    if configured_python is not None:
        olp_python = configured_python
    elif default_venv.exists():
        olp_python = default_venv
    else:
        olp_python = Path(sys.executable)
    target_library = _env_path("OLP_TARGET_LIBRARY", DEFAULT_TARGET_LIBRARY)
    port = int(os.getenv("PORT", "8421"))
    return AppConfig(
        olp_repo_root=repo_root,
        olp_python=olp_python,
        target_library=target_library,
        agent_model=os.getenv("OLP_AGENT_MODEL", "gpt-5.4-mini"),
        port=port,
        run_token=os.getenv("OLP_RUN_TOKEN", ""),
    )


def run_probe(argv: list[str], cwd: Path, timeout_seconds: int = 15) -> str:
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - platform/process dependent
        return f"error: {exc}"
    if completed.returncode == 0:
        return "ok"
    return f"error: {completed.stderr.strip() or completed.stdout.strip()}"


def health(config: AppConfig | None = None) -> HealthResult:
    cfg = config or load_config()
    checks: dict[str, str] = {}
    checks["olp_repo_exists"] = "ok" if cfg.olp_repo_root.exists() else "missing"
    checks["olp_python_exists"] = "ok" if cfg.olp_python.exists() else "missing"
    if cfg.olp_python.exists() and cfg.olp_repo_root.exists():
        checks["olp_imports"] = run_probe(
            [
                str(cfg.olp_python),
                "-c",
                "import obsidian_inventory, obsidian_librarian, obsidian_patron; print('ok')",
            ],
            cfg.olp_repo_root,
        )
        checks["librarian_help"] = run_probe(
            [str(cfg.olp_python), "-m", "obsidian_librarian.cli", "--help"],
            cfg.olp_repo_root,
        )
        checks["patron_help"] = run_probe(
            [str(cfg.olp_python), "-m", "obsidian_patron.cli", "--help"],
            cfg.olp_repo_root,
        )
    else:
        checks["olp_imports"] = "skipped"
        checks["librarian_help"] = "skipped"
        checks["patron_help"] = "skipped"
    status = "ok" if all(value == "ok" for value in checks.values()) else "needs_review"
    return HealthResult(
        status=status,
        olp_repo_root=str(cfg.olp_repo_root),
        olp_python=str(cfg.olp_python),
        target_library=str(cfg.target_library) if cfg.target_library else None,
        openai_api_key_present=bool(os.getenv("OPENAI_API_KEY")),
        agents_sdk_available=agents is not None,
        checks=checks,
    )
