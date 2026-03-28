"""
Socratic debate engine prompts.

All behavioral rules for the chatbot live here. The LLM only receives text built
by this module plus user message and optional pre-fetched source snippets from
the backend ingestion layer — it does not browse or scrape.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Core system instructions (single source of truth for behavior)
# ---------------------------------------------------------------------------

SOCRATIC_DEBATE_SYSTEM_PROMPT_TEMPLATE = """You are a Socratic debate engine. Your ONLY job is to challenge the user's thinking — never to inform, comfort, agree, or take sides.

Debate focus (may be general if not specified): {topic_line}

RULES:
1. Never state your own opinion on the topic. Ever.
2. Never validate the user's position, even partially.
3. Ask ONE sharp question per response. Never two.
4. Use the social media excerpts provided below (when present) to expose contradictions, blind spots, and assumptions. Do NOT dump quotes — choose ONE quote only when it maximally challenges what the user just said. Most turns, use the data invisibly to sharpen your question.
5. Escalate pressure gradually based on turn_index (integer counting this exchange in the thread, starting at 1):
   - Turns 1-2: open, exploratory questions about their core assumption
   - Turns 3-5: identify and expose an internal contradiction in what they've said so far (use prior user lines when provided)
   - Turns 6+: confront them directly with the hardest opposing view they have not addressed (use sources when available)
6. If the user deflects, pivots, or restates without adding substance, name it exactly:
   "You've restated your position. That's not an answer to the question."
7. Responses: 2-3 sentences MAX, then your single question. No lectures. No preamble. Get to the point.
8. When surfacing a quote, format it EXACTLY as:
   QUOTE: "[verbatim text]" — [source]
   Then immediately follow with your question.

Do not claim you browsed the web or scraped platforms. You are only working from the excerpts the backend supplied."""


def _topic_line(topic: str | None) -> str:
    if topic and topic.strip():
        return topic.strip()
    return "(No single topic named — infer from the user's message.)"


def format_source_block_for_prompt(items: list[dict[str, Any]]) -> str:
    """Format normalized source dicts for the user message (not the system prompt)."""
    if not items:
        return "No social media excerpts were supplied for this turn."

    lines: list[str] = ["Social media excerpts (retrieved by the backend, not by you):"]
    for i, item in enumerate(items, start=1):
        src = item.get("source", "unknown")
        label = f"{src}"
        url = item.get("url") or ""
        text = (item.get("excerpt") or item.get("content_text") or "").strip()
        if len(text) > 400:
            text = text[:400] + "…"
        lines.append(f"[{i}] {label} | {url}")
        if text:
            lines.append(f"    {text}")
    return "\n".join(lines)


def build_socratic_system_prompt(topic: str | None) -> str:
    return SOCRATIC_DEBATE_SYSTEM_PROMPT_TEMPLATE.format(topic_line=_topic_line(topic))


def build_socratic_user_content(
    message: str,
    topic: str | None,
    turn_index: int,
    history: list[str],
    source_items: list[dict[str, Any]],
) -> str:
    """Build the user-role message sent to the model."""
    history = [h.strip() for h in history if h and h.strip()][-8:]
    history_block = (
        "Prior user messages in this thread (newest last):\n"
        + "\n".join(f"- {h}" for h in history)
        if history
        else "No prior user messages recorded for this thread."
    )

    return (
        f"turn_index: {turn_index}\n\n"
        f"{history_block}\n\n"
        f"{format_source_block_for_prompt(source_items)}\n\n"
        f"Latest user message:\n{message.strip()}\n"
    )


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
        label = f"{source}" + (f" (@{author})" if author else "")
        out.append(
            {
                "source": source,
                "label": label,
                "url": url,
                "excerpt": str(excerpt) if excerpt else "",
                "platform_id": getattr(obj, "platform_id", None),
            }
        )

    for obj in reddit_items[:max_items]:
        add_from_model(obj)
    return out


def lightweight_sources_for_response(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip heavy fields for API JSON (labels + urls for UI debug)."""
    return [
        {
            "source": it.get("source"),
            "label": it.get("label"),
            "url": it.get("url"),
        }
        for it in items
    ]
