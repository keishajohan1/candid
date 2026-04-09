from app.models.source_content import EngagementMetrics, SourceContent
from app.services.ingestion.rerank_bm25 import rerank_source_contents_by_query


def _item(pid: str, title: str, text: str) -> SourceContent:
    return SourceContent(
        source="reddit",
        platform_id=pid,
        content_type="post",
        url=f"https://reddit.com/{pid}",
        title=title,
        content_text=text,
        engagement=EngagementMetrics(),
    )


def test_rerank_orders_by_query_keyword_match() -> None:
    items = [
        _item("1", "Cats", "meow"),
        _item("2", "Inflation debate", "CPI and federal reserve policy"),
        _item("3", "Sports", "soccer game"),
    ]
    out = rerank_source_contents_by_query(items, "inflation CPI federal reserve")
    assert out[0].platform_id == "2"


def test_rerank_empty_query_returns_original_order() -> None:
    items = [_item("a", "t", "x"), _item("b", "t2", "y")]
    out = rerank_source_contents_by_query(items, "   ")
    assert [x.platform_id for x in out] == ["a", "b"]


def test_rerank_empty_items() -> None:
    assert rerank_source_contents_by_query([], "q") == []
