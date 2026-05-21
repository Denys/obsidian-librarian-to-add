"""Extractor abstractions for optional enrichment."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

from obsidian_librarian.extraction_schema import (
    ExtractionPayload,
    ExtractionValidationError,
    extraction_json_schema,
    validate_extraction_payload,
)


class Extractor(Protocol):
    name: str

    def extract(self, note_content: str, source_ref: str) -> ExtractionPayload:
        """Extract structured payload from staged note content."""


class MockExtractor:
    name = "mock"

    def extract(self, note_content: str, source_ref: str) -> ExtractionPayload:
        snippet = note_content.strip().splitlines()[0] if note_content.strip() else "Empty note"
        payload = {
            "summary": f"Deterministic mock summary for {source_ref}",
            "key_claims": [f"Mock claim derived from: {snippet[:80]}"],
            "action_items": ["Review generated enrichment before promotion."],
            "entities": ["Obsidian Librarian"],
            "source_refs": [source_ref],
            "assumptions": ["Mock extractor does not perform semantic reasoning."],
            "risk_level": "low",
            "confidence": 0.25,
        }
        return validate_extraction_payload(payload)


@dataclass
class OpenAIExtractor:
    model: str = "gpt-5.4-mini"
    name: str = "openai"

    def extract(self, note_content: str, source_ref: str) -> ExtractionPayload:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for --extractor openai")

        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "OpenAI SDK is not installed. Install with: pip install -e '.[llm]'"
            ) from exc

        client = OpenAI(api_key=api_key)
        schema = extraction_json_schema()

        response = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON only; separate claims, assumptions, and actions."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Source reference: {source_ref}\n\nNote content:\n{note_content}",
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "obsidian_extraction",
                    "schema": schema,
                    "strict": True,
                }
            },
        )

        raw = extract_openai_structured_text(response)

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "OpenAI response did not include valid structured JSON output"
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError("OpenAI response JSON payload must be an object")

        try:
            return validate_extraction_payload(payload)
        except ExtractionValidationError as exc:
            raise RuntimeError(f"OpenAI extraction payload failed validation: {exc}") from exc


def extract_openai_structured_text(response: Any) -> str:
    """Extract structured text from OpenAI Responses API result object/dict."""
    status = _get_attr_or_key(response, "status")
    if status == "incomplete":
        details = _get_attr_or_key(response, "incomplete_details", {}) or {}
        reason = _get_attr_or_key(details, "reason")
        if reason:
            raise RuntimeError(f"OpenAI response incomplete: {reason}")
        raise RuntimeError("OpenAI response incomplete")

    output_text = _get_attr_or_key(response, "output_text", "")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = _get_attr_or_key(response, "output", [])
    if not isinstance(output, list):
        raise RuntimeError("OpenAI response output shape is not supported")

    for item in output:
        item_type = _get_attr_or_key(item, "type")
        if item_type and item_type not in {"message", "output_text", "refusal"}:
            continue

        content = _get_attr_or_key(item, "content", [])
        if isinstance(content, list):
            for content_item in content:
                content_type = _get_attr_or_key(content_item, "type")
                if content_type == "refusal":
                    refusal_text = _get_attr_or_key(content_item, "text", "")
                    raise RuntimeError(f"OpenAI refused extraction: {refusal_text or 'refusal'}")
                if content_type == "output_text":
                    text = _get_attr_or_key(content_item, "text", "")
                    if isinstance(text, str) and text.strip():
                        return text.strip()

        if item_type == "refusal":
            refusal_text = _get_attr_or_key(item, "text", "")
            raise RuntimeError(f"OpenAI refused extraction: {refusal_text or 'refusal'}")
        if item_type == "output_text":
            text = _get_attr_or_key(item, "text", "")
            if isinstance(text, str) and text.strip():
                return text.strip()

    raise RuntimeError("OpenAI response did not include structured output text")


def _get_attr_or_key(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)
