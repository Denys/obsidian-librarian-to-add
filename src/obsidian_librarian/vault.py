"""Safe filesystem adapter for Obsidian vault staging writes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from obsidian_librarian.config import LibrarianConfig


class VaultSafetyError(ValueError):
    """Raised when a requested vault operation violates safety rules."""


@dataclass(frozen=True)
class StagedWriteResult:
    """Result returned by a staged write operation."""

    path: Path
    created: bool
    overwritten: bool
    message: str


class ObsidianVault:
    """Filesystem adapter that only permits controlled staged writes."""

    def __init__(self, config: LibrarianConfig) -> None:
        self.config = config

    @property
    def vault_root(self) -> Path:
        """Return the normalized vault root path."""
        return self.config.resolved_vault_root

    @property
    def staging_root(self) -> Path:
        """Return the normalized staging root path."""
        return self.config.staging_root

    def ensure_staging_root(self) -> Path:
        """Create the staging root directory if needed and return it."""
        self.staging_root.mkdir(parents=True, exist_ok=True)
        return self.staging_root

    def resolve_staged_path(self, relative_path: str | Path) -> Path:
        """Resolve a user-supplied path under the staging root.

        Absolute paths and parent traversal are refused. The returned path is normalized and
        guaranteed to remain inside the configured staging directory.
        """
        path = Path(relative_path)

        if path.is_absolute():
            raise VaultSafetyError(f"Staged path must be relative: {relative_path}")

        if not path.parts or str(path) in {"", "."}:
            raise VaultSafetyError("Staged path must point to a file, not the staging root")

        if any(part == ".." for part in path.parts):
            raise VaultSafetyError(f"Parent traversal is not allowed: {relative_path}")

        target = (self.staging_root / path).resolve(strict=False)
        staging_root = self.staging_root.resolve(strict=False)

        if not target.is_relative_to(staging_root):
            raise VaultSafetyError(f"Resolved path escapes staging root: {relative_path}")

        return target

    def next_available_staged_path(self, relative_path: str | Path) -> Path:
        """Return a non-existing staged path derived from a requested relative path."""
        requested = Path(relative_path)
        target = self.resolve_staged_path(requested)

        if not target.exists():
            return target

        parent = requested.parent
        stem = requested.stem
        suffix = requested.suffix

        counter = 1
        while True:
            candidate_relative = parent / f"{stem}_{counter}{suffix}"
            candidate = self.resolve_staged_path(candidate_relative)
            if not candidate.exists():
                return candidate
            counter += 1

    def write_staged_text(
        self,
        relative_path: str | Path,
        content: str,
        *,
        overwrite: bool = False,
        encoding: str = "utf-8",
    ) -> StagedWriteResult:
        """Write text to a staged file.

        Existing files are preserved unless `overwrite=True` is supplied explicitly.
        """
        target = self.resolve_staged_path(relative_path)
        existed = target.exists()

        if existed and not overwrite:
            raise FileExistsError(f"Refusing to overwrite existing staged file: {target}")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)

        return StagedWriteResult(
            path=target,
            created=not existed,
            overwritten=existed,
            message="staged file written" if not existed else "staged file overwritten",
        )

    def write_staged_text_unique(
        self,
        relative_path: str | Path,
        content: str,
        *,
        encoding: str = "utf-8",
    ) -> StagedWriteResult:
        """Write text to the first available staged path without overwriting."""
        target = self.next_available_staged_path(relative_path)
        relative_target = target.relative_to(self.staging_root)
        return self.write_staged_text(relative_target, content, overwrite=False, encoding=encoding)
