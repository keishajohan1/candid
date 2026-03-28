from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=100_000)
    topic: str | None = Field(default=None, max_length=200)
    conversation_id: str | None = None
    """Increment per user-assistant exchange for escalation rules (client-supplied until persistence exists)."""

    turn_index: int = Field(default=1, ge=1, le=500)
    """Prior user-only lines, newest last; used for contradiction detection in prompts."""

    history: list[str] = Field(default_factory=list, max_length=20)

    fetch_sources: bool = Field(
        default=False,
        description="If true, backend runs Reddit/TikTok ingestion before calling the LLM.",
    )
    source_query: str | None = Field(
        default=None,
        max_length=200,
        description="Override query for ingestion; defaults to topic or truncated message.",
    )


class ChatResponse(BaseModel):
    response_text: str
    mode: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    reflection: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(
        default_factory=dict,
        description="Lightweight flags for local testing (counts, ingest errors).",
    )
