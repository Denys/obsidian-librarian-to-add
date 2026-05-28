from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from obsidian_patron.safety import ensure_under

PromotionTarget = Literal["staging", "trusted"]


@dataclass(frozen=True)
class PromotionResult:
    slug: str
    source: Path
    destination: Path
    promoted_to: PromotionTarget
    ledger_path: Path


def promote_to_staging(slug: str, vault_root: str | Path) -> PromotionResult:
    vault = Path(vault_root).expanduser().resolve(strict=False)
    ingestion_root = (vault / "91_Ingestion").resolve(strict=False)
    staging_root = (vault / "90_Staging").resolve(strict=False)
    source = ensure_under(ingestion_root, ingestion_root / slug)
    destination = ensure_under(staging_root, staging_root / slug)
    _validate_directory_move(source=source, destination=destination)

    staging_root.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    ledger_path = _write_ledger(
        destination=destination,
        payload={
            "slug": slug,
            "source": _relative_to_vault(source, vault),
            "destination": _relative_to_vault(destination, vault),
            "promoted_to": "staging",
            "promoted_at": _utc_now(),
            "frontmatter_rewrites": {},
        },
    )
    return PromotionResult(slug, source, destination, "staging", ledger_path)


def promote_to_trusted(
    slug: str,
    vault_root: str | Path,
    *,
    hub: str,
    override: bool = False,
) -> PromotionResult:
    vault = Path(vault_root).expanduser().resolve(strict=False)
    source = _resolve_trusted_source(vault=vault, slug=slug)
    hub_dir = _resolve_hub(vault=vault, hub=hub)
    destination = ensure_under(vault, hub_dir / slug)
    _validate_directory_move(source=source, destination=destination)
    _validate_proposal_gate(source=source, hub=hub, override=override)

    shutil.move(str(source), str(destination))
    promoted_at = _utc_now()
    previous_fields = _rewrite_trusted_frontmatter(
        destination=destination,
        promoted_from=_relative_to_vault(source.parent, vault),
        promoted_at=promoted_at,
        trusted_hub=hub,
    )
    ledger_path = _write_ledger(
        destination=destination,
        payload={
            "slug": slug,
            "source": _relative_to_vault(source, vault),
            "destination": _relative_to_vault(destination, vault),
            "promoted_to": "trusted",
            "promoted_at": promoted_at,
            "frontmatter_rewrites": previous_fields,
        },
    )
    return PromotionResult(slug, source, destination, "trusted", ledger_path)


def unpromote(slug: str, vault_root: str | Path) -> PromotionResult:
    vault = Path(vault_root).expanduser().resolve(strict=False)
    ledger_path = _find_ledger(vault=vault, slug=slug)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    current = ensure_under(vault, ledger_path.parent)
    source = ensure_under(vault, vault / ledger["source"])
    promoted_to = ledger["promoted_to"]
    if source.exists():
        raise FileExistsError(f"Cannot unpromote because original source exists: {source}")

    if promoted_to == "trusted":
        _restore_frontmatter(destination=current, previous_fields=ledger["frontmatter_rewrites"])

    source.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(current), str(source))
    return PromotionResult(slug, current, source, promoted_to, source / "_promotion.json")


def _validate_directory_move(*, source: Path, destination: Path) -> None:
    if not source.exists() or not source.is_dir():
        raise FileNotFoundError(f"Promotion source not found: {source}")
    if destination.exists():
        raise FileExistsError(f"Promotion destination already exists: {destination}")


def _resolve_trusted_source(*, vault: Path, slug: str) -> Path:
    staging = (vault / "90_Staging" / slug).resolve(strict=False)
    ingestion = (vault / "91_Ingestion" / slug).resolve(strict=False)
    if staging.exists():
        return ensure_under(vault, staging)
    if ingestion.exists():
        return ensure_under(vault, ingestion)
    raise FileNotFoundError(f"Promotion source not found for slug: {slug}")


def _resolve_hub(*, vault: Path, hub: str) -> Path:
    hub_path = Path(hub)
    if hub_path.is_absolute():
        raise ValueError("Hub must be a vault-relative path")
    resolved = ensure_under(vault, vault / hub_path)
    if not resolved.exists() or not resolved.is_dir():
        raise FileNotFoundError(f"Trusted hub not found: {resolved}")
    return resolved


def _validate_proposal_gate(*, source: Path, hub: str, override: bool) -> None:
    proposal = source / "_proposal.md"
    if not proposal.exists():
        if override:
            return
        raise ValueError("Trusted promotion requires _proposal.md unless --override is passed")
    selected = _selected_hub(proposal.read_text(encoding="utf-8"))
    if selected == hub:
        return
    if override:
        return
    raise ValueError(f"Proposal selected_hub={selected or 'missing'} does not match --hub {hub}")


def _selected_hub(proposal_text: str) -> str | None:
    match = re.search(r"^-\s*selected_hub:\s*(.+?)\s*$", proposal_text, re.MULTILINE)
    return match.group(1).strip() if match else None


def _rewrite_trusted_frontmatter(
    *, destination: Path, promoted_from: str, promoted_at: str, trusted_hub: str
) -> dict[str, dict[str, str | None]]:
    previous: dict[str, dict[str, str | None]] = {}
    for path in _normal_markdown_files(destination):
        text = path.read_text(encoding="utf-8")
        previous[path.relative_to(destination).as_posix()] = {
            "status": _frontmatter_value(text, "status"),
            "promoted_from": _frontmatter_value(text, "promoted_from"),
            "promoted_at": _frontmatter_value(text, "promoted_at"),
            "trusted_hub": _frontmatter_value(text, "trusted_hub"),
        }
        updated = _set_frontmatter_fields(
            text,
            {
                "status": "trusted",
                "promoted_from": promoted_from,
                "promoted_at": promoted_at,
                "trusted_hub": trusted_hub,
            },
        )
        path.write_text(updated, encoding="utf-8")
    return previous


def _restore_frontmatter(
    *, destination: Path, previous_fields: dict[str, dict[str, str | None]]
) -> None:
    for relative, fields in previous_fields.items():
        path = destination / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        path.write_text(_set_frontmatter_fields(text, fields), encoding="utf-8")


def _normal_markdown_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.rglob("*.md") if not path.name.startswith("_")))


def _frontmatter_value(text: str, key: str) -> str | None:
    frontmatter = _frontmatter(text)
    match = re.search(rf"^{re.escape(key)}:\s*(.*?)\s*$", frontmatter, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip("\"'")


def _set_frontmatter_fields(text: str, fields: dict[str, str | None]) -> str:
    frontmatter, body = _split_frontmatter(text)
    lines = frontmatter.splitlines() if frontmatter else []
    for key, value in fields.items():
        lines = [line for line in lines if not re.match(rf"^{re.escape(key)}:\s*", line)]
        if value is not None:
            lines.append(f"{key}: {value}")
    rendered = "\n".join(lines).strip()
    if rendered:
        return f"---\n{rendered}\n---\n{body.lstrip(chr(10))}"
    return body.lstrip("\n")


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    rest = text.removeprefix("---\n")
    frontmatter, sep, body = rest.partition("\n---\n")
    if not sep:
        return "", text
    return frontmatter, body


def _frontmatter(text: str) -> str:
    return _split_frontmatter(text)[0]


def _write_ledger(*, destination: Path, payload: dict[str, Any]) -> Path:
    ledger_path = destination / "_promotion.json"
    ledger_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ledger_path


def _find_ledger(*, vault: Path, slug: str) -> Path:
    candidates = sorted(vault.rglob(f"{slug}/_promotion.json"))
    if not candidates:
        raise FileNotFoundError(f"Promotion ledger not found for slug: {slug}")
    return candidates[0].resolve(strict=False)


def _relative_to_vault(path: Path, vault: Path) -> str:
    return path.resolve(strict=False).relative_to(vault.resolve(strict=False)).as_posix()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
