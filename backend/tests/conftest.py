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
def _patch_claude_api(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Stub Claude for integration-style tests; unit tests for ClaudeService opt out."""
    if "test_claude_service" in request.node.nodeid:
        return

    async def fake_generate(
        self,
        *,
        system_prompt: str,
        user_content: str,
        sources_for_client: list,
        history: list | None = None,
        allow_verified_knowledge_tool: bool = True,
        **kwargs: object,
    ):
        _ = (system_prompt, user_content, history, allow_verified_knowledge_tool, kwargs)
        return {
            "response_text": "Test assistant reply.",
            "mode": "live",
            "sources": sources_for_client,
            "reflection": {},
        }

    from app.services.claude_service import ClaudeService

    monkeypatch.setattr(ClaudeService, "generate_socratic_response", fake_generate)


@pytest.fixture(autouse=True)
def _patch_reddit_search_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every chat request runs Reddit ingestion; avoid live HTTP in unit tests."""

    async def empty_search(self, **kwargs):  # noqa: ARG001
        from app.models.ingest import IngestResponse

        q = kwargs.get("query") or ""
        return IngestResponse(source="reddit", query=q, items=[], count=0, errors=[])

    from app.services.scrapers.reddit_service import RedditIngestionService

    monkeypatch.setattr(RedditIngestionService, "search", empty_search)
