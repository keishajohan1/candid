from fastapi.testclient import TestClient

from app.main import app


def test_chat_returns_placeholder_when_no_api_key() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        json={"message": "Explain inflation in simple terms."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] in {"mock", "live"}
    assert "response_text" in payload
