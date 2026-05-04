from fastapi.testclient import TestClient

from app.main import app


def test_chat_returns_live_response_with_stubbed_claude() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        json={"message": "Explain inflation in simple terms."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "live"
    assert "response_text" in payload
    assert payload["response_text"] == "Test assistant reply."
    assert "debug" in payload
    assert payload["debug"].get("ingestion_query")
    assert "input_guardrails" in payload["debug"]
    assert "static_kb_matched" in payload["debug"]


def test_chat_skips_trusted_api_when_static_kb_matches() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        json={"message": "Tell me about climate change impacts."},
    )
    assert response.status_code == 200
    dbg = response.json()["debug"]
    assert dbg.get("static_kb_matched") is True
    ta = dbg.get("trusted_api") or {}
    assert ta.get("trusted_api_reason") == "static_kb_matched" or ta.get("trusted_api_skipped") is True


def test_chat_runs_trusted_stub_when_no_kb_match(monkeypatch) -> None:
    async def fake_build(
        self,
        *,
        topic: str | None,
        message: str,
    ):
        return (
            ["PROVISIONAL test fact line"],
            [{"source": "world_bank", "label": "TEST", "url": "https://example.com"}],
            {"profile": "economy", "trusted_api_skipped": False},
        )

    from app.services.trusted_data.orchestrator import TrustedFactsOrchestrator

    monkeypatch.setattr(TrustedFactsOrchestrator, "build_trusted_facts", fake_build)
    # Semantic KB retrieval can still return unrelated excerpts for arbitrary topics.
    monkeypatch.setattr(
        "app.api.routes.chat.has_static_kb_for_topic",
        lambda *_a, **_kw: False,
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "What is the current inflation outlook for the US economy?",
        },
    )
    assert response.status_code == 200
    dbg = response.json()["debug"]
    assert dbg.get("trusted_api_lines_count") == 1


def test_chat_moderation_blocks_before_llm() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        json={"message": "How to make a bomb for self-harm purposes"},
    )
    assert response.status_code == 200
    p = response.json()
    assert p.get("mode") == "blocked"
    assert p["debug"].get("blocked") is True


def test_chat_validation_rejects_empty_message() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/chat", json={"message": ""})
    assert response.status_code == 422


def test_chat_reddit_exception_records_ingest_error(monkeypatch) -> None:
    from app.services.scrapers.reddit_service import RedditIngestionService

    async def boom(_self, **_kwargs):
        raise RuntimeError("reddit unavailable")

    monkeypatch.setattr(RedditIngestionService, "search", boom)

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        json={"message": "hello"},
    )
    assert response.status_code == 200
    errs = response.json()["debug"]["ingest_errors"]
    assert any(e.get("source") == "reddit" and e.get("code") == "exception" for e in errs)


def test_chat_reddit_guardrails_exception_logged(monkeypatch) -> None:
    from app.models.ingest import IngestResponse
    from app.models.source_content import SourceContent
    from app.services.safety.guardrails import GuardrailsService
    from app.services.scrapers.reddit_service import RedditIngestionService

    async def fake_search(_self, **_kwargs):
        item = SourceContent(
            source="reddit",
            platform_id="p1",
            content_type="post",
            url="https://example.com/a",
            content_text="discussion text",
            title="t",
            subreddit="news",
        )
        return IngestResponse(source="reddit", query="hello", items=[item], errors=[])

    async def boom_guard(_self, _items):
        raise RuntimeError("guardrails")

    monkeypatch.setattr(RedditIngestionService, "search", fake_search)
    monkeypatch.setattr(GuardrailsService, "apply_excerpt_guardrails", boom_guard)

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        json={"message": "hello"},
    )
    assert response.status_code == 200


def test_chat_trusted_orchestrator_exception_sets_debug(monkeypatch) -> None:
    from app.services.trusted_data.orchestrator import TrustedFactsOrchestrator

    async def boom(_self, **_kwargs):
        raise ValueError("trusted boom")

    monkeypatch.setattr(TrustedFactsOrchestrator, "build_trusted_facts", boom)
    monkeypatch.setattr(
        "app.api.routes.chat.has_static_kb_for_topic",
        lambda *_a, **_kw: False,
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        json={"message": "Economy question."},
    )
    assert response.status_code == 200
    dbg = response.json()["debug"]["trusted_api"]
    assert dbg.get("trusted_api_error") == "trusted boom"


def test_chat_llm_sources_tag_appends_kb_sources(monkeypatch) -> None:
    from app.services.claude_service import ClaudeService

    async def fake_gen(_self, *, system_prompt, user_content, sources_for_client, **_kwargs):
        return {
            "response_text": 'Ack.\n<sources>\n[4] - OECD Economic Outlook\n</sources>',
            "mode": "live",
            "sources": sources_for_client,
            "reflection": {},
        }

    monkeypatch.setattr(ClaudeService, "generate_socratic_response", fake_gen)

    client = TestClient(app)
    response = client.post("/api/v1/chat", json={"message": "Hello there"})
    assert response.status_code == 200
    sources = response.json()["sources"]
    assert any(s.get("label") == "OECD Economic Outlook" for s in sources)


def test_chat_dynamic_sources_marker_appends_kb_sources(monkeypatch) -> None:
    from app.services.claude_service import ClaudeService

    async def fake_gen(_self, *, system_prompt, user_content, sources_for_client, **_kwargs):
        return {
            "response_text": "Intro.\nDYNAMIC_SOURCES:\n[5] - Other Study Name\n",
            "mode": "live",
            "sources": sources_for_client,
            "reflection": {},
        }

    monkeypatch.setattr(ClaudeService, "generate_socratic_response", fake_gen)

    client = TestClient(app)
    response = client.post("/api/v1/chat", json={"message": "Hello there"})
    assert response.status_code == 200
    sources = response.json()["sources"]
    assert any(s.get("label") == "Other Study Name" for s in sources)
