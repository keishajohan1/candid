"""Coverage for prompt formatters + user-role helpers."""

import types

from app.prompts.formatters import format_source_block_for_prompt
from app.prompts.user_content import (
    build_socratic_user_content,
    lightweight_sources_for_response,
    source_items_for_prompt_from_ingestion,
)


def test_build_socratic_user_content_strips_whitespace() -> None:
    assert "hello" in build_socratic_user_content("  hello  ")


def test_lightweight_sources_for_response_strips_extra_fields() -> None:
    items = [{"source": "a", "label": "l", "url": "u", "extra": "x"}]
    assert lightweight_sources_for_response(items) == [{"source": "a", "label": "l", "url": "u"}]


def test_format_source_block_for_prompt_empty() -> None:
    out = format_source_block_for_prompt([])
    assert "No social media excerpts" in out


def test_format_source_block_truncates_long_excerpt() -> None:
    long_text = "x" * 500
    items = [{"source": "reddit", "url": "", "excerpt": long_text}]
    out = format_source_block_for_prompt(items)
    assert "…" in out
    assert "x" * 200 in out
    assert "x" * 201 not in out


def test_source_items_minimal_model() -> None:
    m = types.SimpleNamespace(
        content_text="body",
        title=None,
        url="http://z",
        source="reddit",
        author=None,
        content_classification=None,
        subreddit=None,
        ideological_lean="neutral",
        platform_id=None,
    )
    out = source_items_for_prompt_from_ingestion([m])
    assert len(out) == 1
    assert out[0]["excerpt"] == "body"


def test_source_items_labels_subreddit_lean_author_classification() -> None:
    m = types.SimpleNamespace(
        content_text=None,
        title="post title",
        url="http://u",
        source="reddit",
        author="me",
        content_classification="news",
        subreddit="news",
        ideological_lean="left",
        platform_id="pid",
    )
    out = source_items_for_prompt_from_ingestion([m])
    lab = out[0]["label"]
    assert "r/news" in lab
    assert "left-leaning" in lab
    assert "@me" in lab
    assert "[Type: news]" in lab


def test_source_items_max_items_cap() -> None:
    rows = []
    for i in range(10):
        rows.append(
            types.SimpleNamespace(
                content_text=str(i),
                title=None,
                url="",
                source="reddit",
                author=None,
                content_classification=None,
                subreddit=None,
                ideological_lean="neutral",
                platform_id=None,
            )
        )
    assert len(source_items_for_prompt_from_ingestion(rows, max_items=5)) == 5
