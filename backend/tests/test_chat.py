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
    assert payload["debug"].get("fetch_sources") is False
    assert "static_kb_matched" in payload["debug"]


def test_chat_skips_trusted_api_when_static_kb_matches() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        json={"message": "Tell me about climate change impacts.", "topic": "climate change"},
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

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "What is the current inflation outlook for the US economy?",
            "topic": "xyzzy_no_kb_bucket_12345",
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
