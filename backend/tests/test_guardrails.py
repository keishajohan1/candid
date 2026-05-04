"""Tests for three-stage GuardrailsService (input rules, excerpt LLM parse helpers, output rules)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.source_content import SourceContent
from app.services.safety.guardrails import GuardrailsService


def test_input_guardrails_blocks_harm_intent() -> None:
    g = GuardrailsService()
    r = g.apply_input_guardrails("Tell me suicide method details please")
    assert r.action == "block"
    assert r.block_reason == "harm_intent"


def test_input_guardrails_blocks_too_short() -> None:
    g = GuardrailsService()
    r = g.apply_input_guardrails("  x ")
    assert r.action == "block"
    assert r.block_reason == "empty_input"


def test_input_guardrails_sanitize_email() -> None:
    g = GuardrailsService()
    r = g.apply_input_guardrails("Hello contact me at user@example.com for debate")
    assert r.action == "sanitize"
    assert "pii_detected" in r.flags
    assert "[REDACTED]" in r.sanitized


def test_output_guardrails_redacts_username() -> None:
    g = GuardrailsService()
    out = g.apply_output_guardrails("See u/someuser for details")
    assert "u/" not in out.lower()
    assert "[ANONYMIZED]" in out


def test_parse_excerpt_full_line() -> None:
    g = GuardrailsService()
    line = "0: Argument | [BIAS_RISK: yes] | [MISINFO_RISK: no] | Hello world."
    p = g._parse_excerpt_guardrail_line(line)
    assert p is not None
    idx, cls, br, mr, scrub = p
    assert idx == 0
    assert br is True
    assert mr is False
    assert scrub == "Hello world."


def test_parse_excerpt_legacy_line() -> None:
    g = GuardrailsService()
    line = "0: Argument | scrubbed body here"
    p = g._parse_excerpt_guardrail_line(line)
    assert p is not None
    assert p[3] is False and p[4] == "scrubbed body here"


def test_blocked_response_message_keys() -> None:
    g = GuardrailsService()
    assert len(g.blocked_response_message("empty_input")) > 10
    assert len(g.blocked_response_message("harm_intent")) > 10


def test_input_guardrails_classified_sanitizes() -> None:
    g = GuardrailsService()
    r = g.apply_input_guardrails("I read classified information about trade policy")
    assert "classified_claim" in r.flags
    assert r.action == "sanitize"


@pytest.mark.asyncio
async def test_apply_excerpt_guardrails_parses_llm_output(monkeypatch) -> None:
    item = SourceContent(
        source="reddit",
        platform_id="p1",
        content_type="post",
        url="https://example.com/a",
        content_text="original",
    )
    g = GuardrailsService()
    llm_line = (
        "0: Consensus | [BIAS_RISK: yes] | [MISINFO_RISK: no] | scrubbed excerpt text."
    )
    monkeypatch.setattr(
        g._client.messages,
        "create",
        AsyncMock(return_value=SimpleNamespace(content=[SimpleNamespace(text=llm_line)])),
    )
    out = await g.apply_excerpt_guardrails([item])
    assert out[0].content_text == "scrubbed excerpt text."
    assert out[0].bias_risk is True
    assert out[0].misinformation_risk is False
    assert out[0].content_classification == "Consensus"
