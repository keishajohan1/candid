from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class EngagementMetrics(BaseModel):
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    views: int | None = None
    score: int | None = None


class SourceContent(BaseModel):
    source: str = Field(..., description="Platform name (e.g. reddit).")
    platform_id: str = Field(..., description="Original platform item ID")
    content_type: str = Field(..., description="post, comment, video, caption, etc.")
    content_classification: str | None = Field(default=None, description="Semantic type: argument, testimony, cited claim, consensus")
    subreddit: str | None = None
    ideological_lean: str | None = None
    author: str | None = None
    url: HttpUrl | str
    title: str | None = None
    content_text: str | None = None
    created_at: datetime | None = None
    engagement: EngagementMetrics = Field(default_factory=EngagementMetrics)
    topic: str | None = None
    query: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
