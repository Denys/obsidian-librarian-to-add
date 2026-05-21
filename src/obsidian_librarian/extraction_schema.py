"""Structured extraction schema and validation for optional LLM enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

RISK_LEVELS = {"low", "medium", "high"}
REQUIRED_KEYS = {
    "summary",
    "key_claims",
    "action_items",
    "entities",
    "source_refs",
    "assumptions",
    "risk_level",
    "confidence",
}


class ExtractionValidationError(ValueError):
    """Raised when an extraction payload does not match the required schema."""


@dataclass(frozen=True)
class ExtractionPayload:
    summary: str
    key_claims: list[str]
    action_items: list[str]
    entities: list[str]
    source_refs: list[str]
    assumptions: list[str]
    risk_level: str
    confidence: float


def extraction_json_schema() -> dict[str, object]:
    """Return JSON schema used for structured output calls."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(REQUIRED_KEYS),
        "properties": {
            "summary": {"type": "string"},
            "key_claims": {"type": "array", "items": {"type": "string"}},
            "action_items": {"type": "array", "items": {"type": "string"}},
            "entities": {"type": "array", "items": {"type": "string"}},
            "source_refs": {"type": "array", "items": {"type": "string"}},
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "risk_level": {"type": "string", "enum": sorted(RISK_LEVELS)},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
    }


def validate_extraction_payload(payload: dict[str, object]) -> ExtractionPayload:
    """Validate extraction payload shape and safety constraints."""
    keys = set(payload)
    missing = REQUIRED_KEYS - keys
    if missing:
        raise ExtractionValidationError(f"Missing required extraction keys: {sorted(missing)}")

    extra = keys - REQUIRED_KEYS
    if extra:
        raise ExtractionValidationError(f"Unexpected extraction keys: {sorted(extra)}")

    summary = _string(payload["summary"], "summary")
    key_claims = _string_list(payload["key_claims"], "key_claims")
    action_items = _string_list(payload["action_items"], "action_items")
    entities = _string_list(payload["entities"], "entities")
    source_refs = _string_list(payload["source_refs"], "source_refs")
    assumptions = _string_list(payload["assumptions"], "assumptions")
    risk_level = _string(payload["risk_level"], "risk_level")

    if risk_level not in RISK_LEVELS:
        raise ExtractionValidationError(f"risk_level must be one of {sorted(RISK_LEVELS)}")

    confidence = payload["confidence"]
    if not isinstance(confidence, (int, float)):
        raise ExtractionValidationError("confidence must be a number")
    confidence_value = float(confidence)
    if confidence_value < 0.0 or confidence_value > 1.0:
        raise ExtractionValidationError("confidence must be between 0.0 and 1.0")

    for ref in source_refs:
        parsed = urlparse(ref)
        if parsed.scheme in {"http", "https"}:
            raise ExtractionValidationError("source_refs may not include external URLs")

    return ExtractionPayload(
        summary=summary,
        key_claims=key_claims,
        action_items=action_items,
        entities=entities,
        source_refs=source_refs,
        assumptions=assumptions,
        risk_level=risk_level,
        confidence=confidence_value,
    )


def _string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ExtractionValidationError(f"{field} must be a string")
    return value


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ExtractionValidationError(f"{field} must be a list of strings")
    return list(value)
