from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    topic: str | None = Field(default=None, max_length=200)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    response_text: str
    mode: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    reflection: dict[str, Any] = Field(default_factory=dict)
