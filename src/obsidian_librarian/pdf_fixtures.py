from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

VALID_STATUSES = {"staged", "failed", "skipped", "needs_review"}
VALID_CLASSIFICATIONS = {
    "digital_pdf",
    "malformed_pdf",
    "scanned_pdf",
    "mixed_pdf",
    "mixed_or_digital_pdf",
}


@dataclass(frozen=True)
class PdfFixture:
    id: str
    file: Path
    role: str
    phase_11_1: dict
    phase_11_2: dict


def load_pdf_fixtures(path: str | Path) -> list[PdfFixture]:
    fixture_path = Path(path)
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture inventory does not exist: {fixture_path}")

    text = fixture_path.read_text(encoding="utf-8")
    data = _parse_yaml_like(text)

    if data.get("schema_version") != 1:
        raise ValueError("fixtures.yaml schema_version must be 1")

    fixture_root = fixture_path.parent
    if not fixture_root.exists():
        raise ValueError(f"fixture_root does not exist: {fixture_root}")

    fixtures = data.get("fixtures")
    if not isinstance(fixtures, list):
        raise ValueError("fixtures must be a list")

    seen_ids: set[str] = set()
    loaded: list[PdfFixture] = []
    for fixture in fixtures:
        fixture_id = fixture.get("id")
        relative_file = fixture.get("file")
        role = fixture.get("role", "")
        phase_11_1 = fixture.get("phase_11_1", {})
        phase_11_2 = fixture.get("phase_11_2", {})

        if not isinstance(fixture_id, str) or not fixture_id:
            raise ValueError("fixture id must be a non-empty string")
        if fixture_id in seen_ids:
            raise ValueError(f"duplicate fixture id: {fixture_id}")
        seen_ids.add(fixture_id)

        if not isinstance(relative_file, str) or not relative_file:
            raise ValueError(f"fixture '{fixture_id}' file must be a non-empty string")
        file_path = Path(relative_file)
        if file_path.is_absolute() or ".." in file_path.parts:
            raise ValueError(f"fixture '{fixture_id}' file must be a safe relative path")

        source = fixture_root / file_path
        if not source.exists():
            raise ValueError(f"fixture '{fixture_id}' PDF does not exist: {source}")

        status = phase_11_1.get("expected_status")
        if status is not None and status not in VALID_STATUSES:
            raise ValueError(f"fixture '{fixture_id}' expected_status is invalid: {status}")

        classification = phase_11_1.get("expected_classification")
        if classification is not None and classification not in VALID_CLASSIFICATIONS:
            raise ValueError(
                f"fixture '{fixture_id}' expected_classification is invalid: {classification}"
            )

        loaded.append(
            PdfFixture(
                id=fixture_id,
                file=file_path,
                role=str(role),
                phase_11_1=dict(phase_11_1),
                phase_11_2=dict(phase_11_2),
            )
        )

    return loaded


def _parse_scalar(raw: str):
    value = raw.strip()
    if value == "true":
        return True
    if value == "false":
        return False
    if value.isdigit():
        return int(value)
    return value


def _parse_yaml_like(text: str) -> dict:
    lines = [
        line.rstrip("\n")
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    i = 0
    root: dict = {}
    while i < len(lines):
        line = lines[i]
        if line.startswith("schema_version:"):
            root["schema_version"] = _parse_scalar(line.split(":", 1)[1])
        elif line.startswith("fixture_root:"):
            root["fixture_root"] = line.split(":", 1)[1].strip()
        elif line.startswith("fixtures:"):
            fixtures: list[dict] = []
            i += 1
            while i < len(lines) and lines[i].startswith("  - "):
                fixture: dict = {}
                first = lines[i].strip()[2:].strip()
                key, value = first.split(":", 1)
                fixture[key.strip()] = _parse_scalar(value)
                i += 1
                while (
                    i < len(lines)
                    and lines[i].startswith("    ")
                    and not lines[i].startswith("  - ")
                ):
                    subline = lines[i][4:]
                    if subline.endswith(":"):
                        section = subline[:-1]
                        i += 1
                        section_obj: dict = {}
                        while i < len(lines) and lines[i].startswith("      "):
                            item = lines[i][6:]
                            if item.startswith("- "):
                                section_obj.setdefault("items", []).append(item[2:].strip())
                            elif item.endswith(":"):
                                nested = item[:-1]
                                i += 1
                                nested_obj: dict = {}
                                while i < len(lines) and lines[i].startswith("        "):
                                    nline = lines[i][8:]
                                    if ":" in nline:
                                        nk, nv = nline.split(":", 1)
                                        nested_obj[nk.strip()] = _parse_scalar(nv)
                                    i += 1
                                section_obj[nested] = nested_obj
                                continue
                            elif ":" in item:
                                k, v = item.split(":", 1)
                                section_obj[k.strip()] = _parse_scalar(v)
                            i += 1
                        fixture[section] = section_obj
                        continue
                    if ":" in subline:
                        k, v = subline.split(":", 1)
                        fixture[k.strip()] = _parse_scalar(v)
                    i += 1
                fixtures.append(fixture)
                continue
            root["fixtures"] = fixtures
            continue
        i += 1
    return root
