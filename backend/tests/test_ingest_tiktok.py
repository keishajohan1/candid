from app.main import app
from app.models.ingest import IngestError, IngestResponse
from app.services.scrapers.tiktok_scraper import TikTokScraperService
from fastapi.testclient import TestClient


def test_tiktok_ingest_route_graceful_error(monkeypatch) -> None:
    async def fake_search(self, query: str, limit: int) -> IngestResponse:  # noqa: ARG001
        return IngestResponse(
            source="tiktok",
            query=query,
            items=[],
            count=0,
            errors=[
                IngestError(
                    code="tiktok_scrape_error",
                    message="TikTok scraping failed.",
                    detail="blocked",
                )
            ],
        )

    monkeypatch.setattr(TikTokScraperService, "search", fake_search)

    client = TestClient(app)
    response = client.post(
        "/api/v1/ingest/tiktok",
        json={"query": "college budgeting", "limit": 2},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "tiktok"
    assert payload["count"] == 0
    assert payload["errors"][0]["code"] == "tiktok_scrape_error"
