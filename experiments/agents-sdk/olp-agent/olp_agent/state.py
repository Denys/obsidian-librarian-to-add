from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from olp_agent.safety import assert_path_inside


def agent_state_dir(target_root: str | Path) -> Path:
    root = Path(target_root).resolve(strict=False)
    return root / ".olp_agent"


def read_state_file(target_root: str | Path, name: str) -> dict[str, Any]:
    root = Path(target_root).resolve(strict=False)
    state_dir = agent_state_dir(root)
    path = assert_path_inside(state_dir / name, [state_dir])
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_state_file(target_root: str | Path, name: str, data: dict[str, Any]) -> Path:
    root = Path(target_root).resolve(strict=False)
    state_dir = agent_state_dir(root)
    state_dir.mkdir(parents=True, exist_ok=True)
    path = assert_path_inside(state_dir / name, [state_dir])
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing state file: {path}")
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return path
