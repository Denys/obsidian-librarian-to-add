"""Compatibility package to support running from a src-layout checkout."""

from __future__ import annotations

from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent
_src_pkg = _pkg_dir.parent / "src" / "obsidian_librarian"

if _src_pkg.is_dir():
    __path__.append(str(_src_pkg))

__version__ = "0.1.0"
