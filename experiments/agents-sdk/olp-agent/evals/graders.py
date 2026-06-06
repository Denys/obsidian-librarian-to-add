from __future__ import annotations

from pathlib import Path


def assert_path_exists(path: Path) -> None:
    if not path.exists():
        raise AssertionError(f"Expected path to exist: {path}")


def assert_status(value: str, expected: str, case_id: str) -> None:
    if value != expected:
        raise AssertionError(f"{case_id}: expected status {expected}, got {value}")
