from __future__ import annotations

import sys

import pytest

from obsidian_librarian.extractors import (
    MockExtractor,
    OpenAIExtractor,
    extract_openai_structured_text,
)


def test_mock_extractor_returns_valid_payload() -> None:
    out = MockExtractor().extract("# Title", "90_Staging/Sources/note.md")
    assert out.summary
    assert out.source_refs == ["90_Staging/Sources/note.md"]


def test_openai_extractor_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        OpenAIExtractor().extract("x", "y")


def test_extract_openai_structured_text_uses_output_text_primary() -> None:
    class DummyResponse:
        output_text = '{"summary": "ok"}'

    assert extract_openai_structured_text(DummyResponse()) == '{"summary": "ok"}'


def test_extract_openai_structured_text_fallback_nested_output_text() -> None:
    response = {
        "output": [{"type": "message", "content": [{"type": "output_text", "text": '{"a":1}'}]}]
    }
    assert extract_openai_structured_text(response) == '{"a":1}'


def test_extract_openai_structured_text_refusal_fails() -> None:
    response = {
        "output": [{"type": "message", "content": [{"type": "refusal", "text": "policy"}]}]
    }
    with pytest.raises(RuntimeError, match="refused"):
        extract_openai_structured_text(response)


def test_extract_openai_structured_text_incomplete_fails() -> None:
    response = {"status": "incomplete"}
    with pytest.raises(RuntimeError, match="incomplete"):
        extract_openai_structured_text(response)


def test_extract_openai_structured_text_incomplete_reason_fails() -> None:
    response = {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}
    with pytest.raises(RuntimeError, match="max_output_tokens"):
        extract_openai_structured_text(response)


def test_extract_openai_structured_text_unknown_shape_fails() -> None:
    with pytest.raises(RuntimeError, match="structured output text"):
        extract_openai_structured_text({"output": []})


def test_openai_extractor_rejects_non_json_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    class DummyResponse:
        output_text = "not json"

    class DummyClient:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key
            self.responses = self

        def create(self, **_: object) -> DummyResponse:
            return DummyResponse()

    class DummyModule:
        OpenAI = DummyClient

    sys.modules["openai"] = DummyModule()
    with pytest.raises(RuntimeError, match="structured JSON"):
        OpenAIExtractor().extract("x", "90_Staging/Sources/a.md")
    sys.modules.pop("openai", None)


def test_openai_extractor_invalid_schema_payload_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    class DummyResponse:
        output_text = '{"summary": "ok"}'

    class DummyClient:
        def __init__(self, api_key: str) -> None:
            self.responses = self

        def create(self, **_: object) -> DummyResponse:
            return DummyResponse()

    class DummyModule:
        OpenAI = DummyClient

    sys.modules["openai"] = DummyModule()
    with pytest.raises(RuntimeError, match="failed validation"):
        OpenAIExtractor().extract("x", "90_Staging/Sources/a.md")
    sys.modules.pop("openai", None)
