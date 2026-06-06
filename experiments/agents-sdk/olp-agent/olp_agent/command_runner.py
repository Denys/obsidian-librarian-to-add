from __future__ import annotations

import subprocess
import time
from pathlib import Path

from olp_agent.schemas import ExecutedCommand
from olp_agent.safety import ensure_no_unsafe_argv


def _trim(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[trimmed]"


def run_command(
    label: str,
    argv: list[str],
    cwd: str | Path,
    timeout_seconds: int = 120,
) -> ExecutedCommand:
    ensure_no_unsafe_argv(argv)
    start = time.perf_counter()
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        elapsed = int((time.perf_counter() - start) * 1000)
        return ExecutedCommand(
            label=label,
            argv=argv,
            exit_code=completed.returncode,
            duration_ms=elapsed,
            stdout=_trim(completed.stdout),
            stderr=_trim(completed.stderr),
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = int((time.perf_counter() - start) * 1000)
        return ExecutedCommand(
            label=label,
            argv=argv,
            exit_code=None,
            duration_ms=elapsed,
            timed_out=True,
            stdout=_trim((exc.stdout or "").decode() if isinstance(exc.stdout, bytes) else exc.stdout or ""),
            stderr=_trim((exc.stderr or "").decode() if isinstance(exc.stderr, bytes) else exc.stderr or ""),
        )
