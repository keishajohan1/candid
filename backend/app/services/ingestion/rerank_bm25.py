"""Lexical rerank for social (Reddit) candidates — query relevance within Tier 2."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _doc_text(item: Any) -> str:
    title = getattr(item, "title", None) or ""
    body = getattr(item, "content_text", None) or ""
    sub = getattr(item, "subreddit", None) or ""
    return f"{title} {body} {sub}".strip()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def rerank_source_contents_by_query(items: list[Any], query: str) -> list[Any]:
    """BM25 order by query; returns new list (stable if rank-bm25 missing or empty query)."""
    if not items or not (query or "").strip():
        return list(items)
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        logger.warning("rank-bm25 not installed; skipping BM25 rerank")
        return list(items)

    corpus = [_tokenize(_doc_text(it)) for it in items]
    q_tokens = _tokenize(query)
    if not q_tokens:
        return list(items)
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(q_tokens)
    order = sorted(range(len(items)), key=lambda i: scores[i], reverse=True)
    return [items[i] for i in order]
