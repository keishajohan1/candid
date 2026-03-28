from pydantic import BaseModel, Field

from app.models.source_content import SourceContent


class RedditIngestRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(default=25, ge=1, le=50)
    include_top_comments: bool = Field(default=False)
    comments_limit: int = Field(default=5, ge=1, le=20)
    topic: str = Field(default="", max_length=200)
    turn: int = Field(default=0, ge=0, le=10_000)


class IngestError(BaseModel):
    code: str
    message: str
    detail: str | None = None


class IngestResponse(BaseModel):
    source: str
    query: str
    items: list[SourceContent] = Field(default_factory=list)
    count: int = 0
    errors: list[IngestError] = Field(default_factory=list)
