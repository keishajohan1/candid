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
