"""User-role message assembly and client-facing source normalization."""

from typing import Any


def build_socratic_user_content(message: str) -> str:
    """Build the user-role message sent to the model."""
    return f"Latest user message:\n{message.strip()}\n"


def source_items_for_prompt_from_ingestion(
    reddit_items: list[Any],
    max_items: int = 5,
) -> list[dict[str, Any]]:
    """Convert SourceContent-like objects (Pydantic models) to prompt-friendly dicts."""
    out: list[dict[str, Any]] = []

    def add_from_model(obj: Any) -> None:
        excerpt = getattr(obj, "content_text", None) or getattr(obj, "title", None) or ""
        url = str(getattr(obj, "url", "") or "")
        source = getattr(obj, "source", "unknown")
        author = getattr(obj, "author", None)
        classification = getattr(obj, "content_classification", None)
        subreddit = getattr(obj, "subreddit", None)
        lean = getattr(obj, "ideological_lean", None)

        label_parts = [source]
        if subreddit:
            label_parts.append(f"r/{subreddit}")
        if lean and lean != "neutral":
            label_parts.append(f"({lean}-leaning)")
        if author:
            label_parts.append(f"@{author}")
        if classification:
            label_parts.append(f"[Type: {classification}]")

        label = " | ".join(label_parts)

        out.append(
            {
                "source": source,
                "label": label,
                "url": url,
                "excerpt": str(excerpt) if excerpt else "",
                "platform_id": getattr(obj, "platform_id", None),
                "bias_risk": getattr(obj, "bias_risk", None),
                "misinformation_risk": getattr(obj, "misinformation_risk", None),
            }
        )

    for obj in reddit_items[:max_items]:
        add_from_model(obj)
    return out


def lightweight_sources_for_response(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip heavy fields for API JSON (labels + UI display purposes)."""
    return [
        {
            "source": it.get("source"),
            "label": it.get("label"),
            "url": it.get("url"),
        }
        for it in items
    ]
