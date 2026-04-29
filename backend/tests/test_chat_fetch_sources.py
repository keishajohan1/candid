from fastapi.testclient import TestClient

from app.main import app
from app.models.ingest import IngestResponse
from app.models.source_content import EngagementMetrics, SourceContent
from app.services.scrapers.reddit_service import RedditIngestionService
from app.services.safety.guardrails import GuardrailsService


def test_chat_reddit_reranks_and_calls_guardrails(monkeypatch) -> None:
    items = [
        SourceContent(
            source="reddit",
            platform_id="1",
            content_type="post",
            url="https://reddit.com/1",
            title="Sports scores",
            content_text="soccer match",
            engagement=EngagementMetrics(score=10),
            raw_payload={},
        ),
        SourceContent(
            source="reddit",
            platform_id="2",
            content_type="post",
            url="https://reddit.com/2",
            title="Inflation thread",
            content_text="CPI federal reserve inflation policy debate",
            engagement=EngagementMetrics(score=12),
            raw_payload={},
        ),
    ]

    async def fake_search(self, **kwargs) -> IngestResponse:  # noqa: ARG001
        return IngestResponse(
            source="reddit",
            query=kwargs.get("query", ""),
            items=items,
            count=len(items),
            errors=[],
        )

    async def fake_guard(self, items):  # noqa: ARG001
        return items

    monkeypatch.setattr(RedditIngestionService, "search", fake_search)
    monkeypatch.setattr(GuardrailsService, "apply_excerpt_guardrails", fake_guard)

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "What drives inflation today?",
            "source_query": "inflation CPI federal reserve",
        },
    )
    assert response.status_code == 200
    dbg = response.json()["debug"]
    assert dbg.get("reddit_item_count") == 2
    assert dbg.get("ingestion_query") == "What drives inflation today?"
