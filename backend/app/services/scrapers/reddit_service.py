import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.models.ingest import IngestError, IngestResponse
from app.models.source_content import EngagementMetrics, SourceContent
from app.services.ingestion.deduper import dedupe_items
from app.services.ingestion.normalizer import normalize_items

logger = logging.getLogger(__name__)

SORT_STRATEGIES = ["relevance", "top", "new", "hot", "comments"]

SUBREDDITS_BY_TOPIC: dict[str, list[str]] = {
    "climate change": ["climate", "environment", "collapse", "climateskeptics", "worldnews"],
    "immigration": ["immigration", "politics", "worldnews", "conservative", "liberal"],
    "economy": ["economics", "economy", "personalfinance", "antiwork", "wallstreetbets"],
    "elections": ["politics", "Ask_Politics", "Conservative", "Liberal", "worldnews"],
    "telecoms": ["technology", "netsec", "worldnews", "geopolitics", "Futurology"],
    "telecommunications": ["technology", "netsec", "worldnews", "geopolitics", "Futurology"],
}

DEFAULT_SUBREDDITS = ["worldnews", "politics", "changemyview", "AskReddit"]

# Cap concurrent comment-thread fetches if include_top_comments is enabled.
_REDDIT_SEMAPHORE = asyncio.Semaphore(3)

# No HTTP response caching — each request hits Reddit fresh.


class RedditIngestionService:
    """Reddit ingestion via global search + parallel subreddit searches (public JSON)."""

    async def search(
        self,
        query: str,
        limit: int = 25,
        include_top_comments: bool = False,
        comments_limit: int = 5,
        turn: int = 0,
        topic: str = "",
    ) -> IngestResponse:
        start = time.monotonic()
        headers = {"User-Agent": settings.reddit_user_agent}
        errors: list[IngestError] = []
        items: list[SourceContent] = []

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                posts = await self._search_all_sources(
                    client=client,
                    query=query,
                    topic=topic,
                    limit=limit,
                    headers=headers,
                    turn=turn,
                )
                posts = [p for p in posts if self._is_quality_post(p)]
                for post in posts:
                    items.append(self._to_post_item(post, query))
                    if include_top_comments:
                        try:
                            comments = await self._fetch_top_comments(
                                client=client,
                                subreddit=post.get("subreddit", ""),
                                post_id=post.get("id", ""),
                                comments_limit=comments_limit,
                                headers=headers,
                                query=query,
                            )
                            items.extend(comments)
                        except Exception as exc:  # noqa: BLE001
                            logger.debug(
                                "Skipping comments for post %s: %s",
                                post.get("id"),
                                exc,
                            )
                        await asyncio.sleep(0.3)

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
        rng = random.Random(turn)
        rng.shuffle(normalized)
        elapsed = time.monotonic() - start
        logger.info(
            "Reddit ingestion complete: %d items in %.1fs (turn=%d)",
            len(normalized),
            elapsed,
            turn,
        )
        return IngestResponse(
            source="reddit",
            query=query,
            items=normalized[:30],
            count=min(len(normalized), 30),
            errors=errors,
        )

    async def _search_all_sources(
        self,
        client: httpx.AsyncClient,
        query: str,
        topic: str,
        limit: int,
        headers: dict[str, str],
        turn: int,
    ) -> list[dict[str, Any]]:
        subreddits = SUBREDDITS_BY_TOPIC.get(topic.lower(), DEFAULT_SUBREDDITS)
        tasks: list[Any] = [
            self._search_posts(client, query, limit, headers, turn),
        ]
        for sub in subreddits[:3]:
            tasks.append(
                self._search_subreddit(client, sub, query, limit // 2, headers)
            )
        results = await asyncio.gather(*tasks, return_exceptions=True)
        posts: list[dict[str, Any]] = []
        for r in results:
            if isinstance(r, list):
                posts.extend(r)
        return posts

    def _is_quality_post(self, post: dict[str, Any]) -> bool:
        score = post.get("score", 0) or 0
        selftext = post.get("selftext", "") or ""
        title = post.get("title", "") or ""
        if post.get("stickied"):
            return False
        if selftext in ("[deleted]", "[removed]", ""):
            pass  # title-only posts are fine
        if score < 5:
            return False
        if len(title) < 20:
            return False
        return True

    async def _search_posts(
        self,
        client: httpx.AsyncClient,
        query: str,
        limit: int,
        headers: dict[str, str],
        turn: int = 0,
    ) -> list[dict[str, Any]]:
        sort = SORT_STRATEGIES[turn % len(SORT_STRATEGIES)]
        response = await client.get(
            "https://www.reddit.com/search.json",
            params={
                "q": query,
                "limit": limit,
                "sort": sort,
                "t": "month",
                "restrict_sr": False,
            },
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()
        children = payload.get("data", {}).get("children", [])
        return [child.get("data", {}) for child in children]

    async def _search_subreddit(
        self,
        client: httpx.AsyncClient,
        subreddit: str,
        query: str,
        limit: int,
        headers: dict[str, str],
    ) -> list[dict[str, Any]]:
        try:
            response = await client.get(
                f"https://www.reddit.com/r/{subreddit}/search.json",
                params={
                    "q": query,
                    "limit": limit,
                    "sort": "top",
                    "t": "year",
                    "restrict_sr": True,
                },
                headers=headers,
            )
            if response.status_code in (403, 404, 429):
                logger.debug(
                    "Subreddit %s returned %s, skipping",
                    subreddit,
                    response.status_code,
                )
                return []
            response.raise_for_status()
            payload = response.json()
            children = payload.get("data", {}).get("children", [])
            return [child.get("data", {}) for child in children]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Subreddit %s search failed: %s", subreddit, exc)
            return []

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
        try:
            async with _REDDIT_SEMAPHORE:
                response = await client.get(
                    f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json",
                    params={"limit": comments_limit, "sort": "top"},
                    headers=headers,
                )
                if response.status_code in (403, 404, 429):
                    logger.debug(
                        "Skipping comments for %s/%s: HTTP %s",
                        subreddit,
                        post_id,
                        response.status_code,
                    )
                    return []
                response.raise_for_status()
                payload = response.json()
                if len(payload) < 2:
                    return []

                comments = payload[1].get("data", {}).get("children", [])
                results: list[SourceContent] = []
                for child in comments:
                    data = child.get("data", {})
                    body = data.get("body")
                    if not body or body in ("[deleted]", "[removed]"):
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
                            content_text=body,
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
        except httpx.HTTPStatusError as exc:
            logger.debug("Comment fetch blocked for %s/%s: %s", subreddit, post_id, exc)
            return []
        except Exception as exc:  # noqa: BLE001
            logger.debug("Comment fetch failed for %s/%s: %s", subreddit, post_id, exc)
            return []

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
