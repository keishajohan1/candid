"""
Tests require ANTHROPIC_API_KEY in the environment before `app` is imported.
We set a dummy value and stub Claude API calls so no real network requests run.
"""

import os

# Force a non-empty key so Settings() succeeds even if backend/.env is empty locally.
os.environ["ANTHROPIC_API_KEY"] = (
    "sk-ant-api03-test000000000000000000000000000000000000000000000000000000000000"
)

import pytest


@pytest.fixture(autouse=True)
def _patch_claude_api(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_generate(
        self,
        *,
        system_prompt: str,
        user_content: str,
        sources_for_client: list,
    ):
        return {
            "response_text": "Test assistant reply.",
            "mode": "live",
            "sources": sources_for_client,
            "reflection": {},
        }

    from app.services.claude_service import ClaudeService

    monkeypatch.setattr(ClaudeService, "generate_socratic_response", fake_generate)
