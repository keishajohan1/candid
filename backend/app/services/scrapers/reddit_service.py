import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.models.ingest import IngestError, IngestResponse
from app.models.source_content import EngagementMetrics, SourceContent
from app.services.ingestion.deduper import dedupe_items
from app.services.ingestion.normalizer import normalize_items

logger = logging.getLogger(__name__)


class RedditIngestionService:
    """Reddit search ingestion using public JSON endpoints."""

    async def search(
        self,
        query: str,
        limit: int = 10,
        include_top_comments: bool = False,
        comments_limit: int = 3,
    ) -> IngestResponse:
        headers = {"User-Agent": settings.reddit_user_agent}
        errors: list[IngestError] = []
        items: list[SourceContent] = []

        try:
            async with httpx.AsyncClient(timeout=settings.reddit_timeout_seconds) as client:
                posts = await self._search_posts(client, query, limit, headers)
                for post in posts:
                    items.append(self._to_post_item(post, query))
                    if include_top_comments:
                        comments = await self._fetch_top_comments(
                            client=client,
                            subreddit=post.get("subreddit", ""),
                            post_id=post.get("id", ""),
                            comments_limit=comments_limit,
                            headers=headers,
                            query=query,
                        )
                        items.extend(comments)
        except httpx.HTTPError as exc:
            logger.warning("Reddit ingestion HTTP error: %s", exc)
            errors.append(
                IngestError(
                    code="reddit_http_error",
                    message="Reddit ingestion failed due to network/API error.",
                    detail=str(exc),
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected Reddit ingestion error: %s", exc)
            errors.append(
                IngestError(
                    code="reddit_unexpected_error",
                    message="Unexpected Reddit ingestion failure.",
                    detail=str(exc),
                )
            )

        normalized = dedupe_items(normalize_items(items))
        return IngestResponse(
            source="reddit",
            query=query,
            items=normalized,
            count=len(normalized),
            errors=errors,
        )

    async def _search_posts(
        self,
        client: httpx.AsyncClient,
        query: str,
        limit: int,
        headers: dict[str, str],
    ) -> list[dict[str, Any]]:
        response = await client.get(
            "https://www.reddit.com/search.json",
            params={"q": query, "limit": limit, "sort": "relevance", "restrict_sr": False},
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()
        children = payload.get("data", {}).get("children", [])
        return [child.get("data", {}) for child in children]

    async def _fetch_top_comments(
        self,
        client: httpx.AsyncClient,
        subreddit: str,
        post_id: str,
        comments_limit: int,
        headers: dict[str, str],
        query: str,
    ) -> list[SourceContent]:
        if not subreddit or not post_id:
            return []

        response = await client.get(
            f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json",
            params={"limit": comments_limit, "sort": "top"},
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()
        if len(payload) < 2:
            return []

        comments = payload[1].get("data", {}).get("children", [])
        results: list[SourceContent] = []
        for child in comments:
            data = child.get("data", {})
            if data.get("body") is None:
                continue
            created = self._unix_to_datetime(data.get("created_utc"))
            results.append(
                SourceContent(
                    source="reddit",
                    platform_id=data.get("id", ""),
                    content_type="comment",
                    author=data.get("author"),
                    url=f"https://www.reddit.com{data.get('permalink', '')}",
                    title=None,
                    content_text=data.get("body"),
                    created_at=created,
                    engagement=EngagementMetrics(
                        score=data.get("score"),
                        likes=None,
                        comments=None,
                        shares=None,
                        views=None,
                    ),
                    query=query,
                    raw_payload=data,
                )
            )
        return results

    def _to_post_item(self, data: dict[str, Any], query: str) -> SourceContent:
        created = self._unix_to_datetime(data.get("created_utc"))
        permalink = data.get("permalink", "")
        post_url = f"https://www.reddit.com{permalink}" if permalink else data.get("url", "")
        return SourceContent(
            source="reddit",
            platform_id=data.get("id", ""),
            content_type="post",
            author=data.get("author"),
            url=post_url,
            title=data.get("title"),
            content_text=data.get("selftext") or data.get("title"),
            created_at=created,
            engagement=EngagementMetrics(
                score=data.get("score"),
                comments=data.get("num_comments"),
                likes=None,
                shares=None,
                views=None,
            ),
            query=query,
            raw_payload=data,
        )

    @staticmethod
    def _unix_to_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (TypeError, ValueError):
            return None
