from app.main import app
from app.models.ingest import IngestResponse
from app.models.source_content import EngagementMetrics, SourceContent
from app.services.scrapers.reddit_service import RedditIngestionService
from fastapi.testclient import TestClient


def test_reddit_ingest_route_with_mocked_service(monkeypatch) -> None:
    async def fake_search(self, query: str, limit: int, include_top_comments: bool, comments_limit: int) -> IngestResponse:  # noqa: ARG001
        return IngestResponse(
            source="reddit",
            query=query,
            items=[
                SourceContent(
                    source="reddit",
                    platform_id="abc123",
                    content_type="post",
                    author="user1",
                    url="https://www.reddit.com/r/test/comments/abc123/example/",
                    title="Example",
                    content_text="Some text",
                    engagement=EngagementMetrics(score=10, comments=2),
                    raw_payload={},
                )
            ],
            count=1,
            errors=[],
        )

    monkeypatch.setattr(RedditIngestionService, "search", fake_search)

    client = TestClient(app)
    response = client.post(
        "/api/v1/ingest/reddit",
        json={"query": "inflation", "limit": 3, "include_top_comments": True, "comments_limit": 2},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "reddit"
    assert payload["count"] == 1
    assert payload["items"][0]["platform_id"] == "abc123"
    assert payload["errors"] == []
