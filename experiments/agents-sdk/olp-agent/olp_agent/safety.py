from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel


class ApprovalSet(BaseModel):
    approve_create_infrastructure: bool = False
    approve_staging_write: bool = False
    approve_ocr: bool = False
    approve_llm: bool = False
    approve_large_pdf_ingest: bool = False
    approve_launch_gui: bool = False
    approve_promotion: bool = False
    approve_unpromotion: bool = False
    approve_force_overwrite: bool = False


class ApprovalOutcome(BaseModel):
    status: str
    required_approvals: list[str]


def canonical_path(path: str | Path) -> Path:
    raw = Path(path).expanduser()
    text = str(raw)
    if text.startswith("\\\\"):
        raise ValueError(f"UNC paths are not allowed: {path}")
    return raw.resolve(strict=False)


def _casefold_path(path: Path) -> str:
    text = str(path)
    return text.casefold() if os.name == "nt" else text


def assert_path_inside(path: str | Path, allowed_roots: Iterable[str | Path]) -> Path:
    candidate = canonical_path(path)
    candidate_text = _casefold_path(candidate)
    for root in allowed_roots:
        root_path = canonical_path(root)
        root_text = _casefold_path(root_path)
        if candidate_text == root_text or candidate_text.startswith(root_text.rstrip("\\/") + os.sep):
            return candidate
    raise ValueError(f"Path is outside allowed roots: {candidate}")


def require_approval(required: list[str], approvals: ApprovalSet) -> ApprovalOutcome:
    missing = [flag for flag in required if not getattr(approvals, flag)]
    if missing:
        return ApprovalOutcome(status="needs_approval", required_approvals=missing)
    return ApprovalOutcome(status="ok", required_approvals=[])


def ensure_no_unsafe_argv(argv: list[str]) -> None:
    if not argv:
        raise ValueError("Command argv cannot be empty")
    joined = " ".join(argv)
    if any(token in joined for token in ["&&", "||", ";", "|"]):
        raise ValueError(f"Shell control operators are not allowed in argv: {joined}")
    if "--vault" in argv:
        value = argv[argv.index("--vault") + 1]
        if value == ".":
            raise ValueError("Explicit --vault cannot be '.'")
    if "obsidian_librarian.cli" in argv and "ingest" in argv and "--mode" not in argv:
        raise ValueError("Librarian ingest requires explicit --mode")
