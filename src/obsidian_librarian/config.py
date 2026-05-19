"""Configuration models for Obsidian Librarian.

The configuration layer is intentionally small in Phase 2. It only defines vault and staging
paths used by the safe staged writer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_STAGING_DIR_NAME = "90_Staging"


@dataclass(frozen=True)
class LibrarianConfig:
    """Filesystem configuration for a librarian run."""

    vault_root: Path
    staging_dir_name: str = DEFAULT_STAGING_DIR_NAME

    @classmethod
    def from_paths(
        cls,
        vault_root: str | Path,
        staging_dir_name: str = DEFAULT_STAGING_DIR_NAME,
    ) -> LibrarianConfig:
        """Create a config from user supplied paths."""
        return cls(vault_root=Path(vault_root).expanduser(), staging_dir_name=staging_dir_name)

    @property
    def resolved_vault_root(self) -> Path:
        """Return the normalized vault root path without requiring it to exist."""
        return self.vault_root.resolve(strict=False)

    @property
    def staging_root(self) -> Path:
        """Return the normalized staging root path."""
        return (self.resolved_vault_root / self.staging_dir_name).resolve(strict=False)
