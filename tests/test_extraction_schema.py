from __future__ import annotations

import pytest

from obsidian_librarian.extraction_schema import (
    ExtractionValidationError,
    validate_extraction_payload,
)


def base_payload() -> dict[str, object]:
    return {
        "summary": "s",
        "key_claims": ["a"],
        "action_items": ["b"],
        "entities": ["c"],
        "source_refs": ["90_Staging/Sources/a.md"],
        "assumptions": ["d"],
        "risk_level": "low",
        "confidence": 0.5,
    }


def test_valid_payload_passes() -> None:
    assert validate_extraction_payload(base_payload()).confidence == 0.5


def test_missing_field_fails() -> None:
    payload = base_payload()
    payload.pop("summary")
    with pytest.raises(ExtractionValidationError):
        validate_extraction_payload(payload)


def test_confidence_range_fails() -> None:
    payload = base_payload()
    payload["confidence"] = 2
    with pytest.raises(ExtractionValidationError):
        validate_extraction_payload(payload)


def test_external_source_ref_fails() -> None:
    payload = base_payload()
    payload["source_refs"] = ["https://example.com"]
    with pytest.raises(ExtractionValidationError):
        validate_extraction_payload(payload)
