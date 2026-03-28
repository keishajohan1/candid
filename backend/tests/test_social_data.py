from fastapi.testclient import TestClient

from app.main import app
from app.models.ingest import IngestError, IngestResponse
from app.models.source_content import EngagementMetrics, SourceContent
from app.services.scrapers.reddit_service import RedditIngestionService


def _reddit_post() -> SourceContent:
    return SourceContent(
        source="reddit",
        platform_id="p1",
        content_type="post",
        author="u",
        url="https://www.reddit.com/r/test/comments/p1/x/",
        title="Example post title here",
        content_text="Some text",
        engagement=EngagementMetrics(score=10, comments=2),
        raw_payload={},
    )


def test_social_data_returns_reddit_response(monkeypatch) -> None:
    async def fake_reddit(self, **kwargs) -> IngestResponse:  # noqa: ARG001
        return IngestResponse(
            source="reddit",
            query=kwargs.get("query", ""),
            items=[_reddit_post()],
            count=1,
            errors=[],
        )

    monkeypatch.setattr(RedditIngestionService, "search", fake_reddit)

    client = TestClient(app)
    response = client.get("/api/v1/social-data", params={"topic": "economy", "turn": 0})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "reddit"
    assert body["count"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["source"] == "reddit"


def test_social_data_empty_items_still_200(monkeypatch) -> None:
    async def fake_reddit(self, **kwargs) -> IngestResponse:  # noqa: ARG001
        return IngestResponse(
            source="reddit",
            query="",
            items=[],
            count=0,
            errors=[],
        )

    monkeypatch.setattr(RedditIngestionService, "search", fake_reddit)

    client = TestClient(app)
    response = client.get("/api/v1/social-data", params={"topic": "telecoms"})
    assert response.status_code == 200
    assert response.json()["source"] == "reddit"
    assert response.json()["count"] == 0


def test_social_data_preserves_reddit_errors(monkeypatch) -> None:
    async def reddit_with_error(self, **kwargs) -> IngestResponse:  # noqa: ARG001
        return IngestResponse(
            source="reddit",
            query="q",
            items=[],
            count=0,
            errors=[IngestError(code="reddit_http_error", message="network", detail="timeout")],
        )

    monkeypatch.setattr(RedditIngestionService, "search", reddit_with_error)

    client = TestClient(app)
    response = client.get("/api/v1/social-data", params={"topic": "immigration", "turn": 2})
    assert response.status_code == 200
    errs = response.json()["errors"]
    assert len(errs) == 1
    assert errs[0]["code"] == "reddit_http_error"


def test_social_data_passes_turn_topic_and_query_to_reddit(monkeypatch) -> None:
    captured: dict = {}

    async def capture(self, **kwargs) -> IngestResponse:
        captured.clear()
        captured.update(kwargs)
        return IngestResponse(source="reddit", query="", items=[], count=0, errors=[])

    monkeypatch.setattr(RedditIngestionService, "search", capture)

    client = TestClient(app)
    client.get(
        "/api/v1/social-data",
        params={"topic": "immigration", "turn": 7, "q": "border policy"},
    )
    assert captured.get("turn") == 7
    assert captured.get("topic") == "immigration"
    assert captured.get("query") == "border policy"


def test_social_data_empty_topic_uses_world_news_fallback(monkeypatch) -> None:
    seen: dict[str, str] = {}

    async def reddit(self, **kwargs) -> IngestResponse:
        seen["query"] = kwargs.get("query", "")
        seen["topic"] = kwargs.get("topic", "")
        return IngestResponse(
            source="reddit",
            query=seen["query"],
            items=[],
            count=0,
            errors=[],
        )

    monkeypatch.setattr(RedditIngestionService, "search", reddit)

    client = TestClient(app)
    response = client.get("/api/v1/social-data", params={"topic": "", "turn": 0})
    assert response.status_code == 200
    assert seen["query"] == "world news"
    assert seen["topic"] == "world news"
