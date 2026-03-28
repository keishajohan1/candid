from fastapi import APIRouter

from app.models.ingest import IngestResponse, RedditIngestRequest
from app.services.scrapers.reddit_service import RedditIngestionService

router = APIRouter()


@router.post("/ingest/reddit", response_model=IngestResponse)
async def ingest_reddit(payload: RedditIngestRequest) -> IngestResponse:
    service = RedditIngestionService()
    return await service.search(
        query=payload.query,
        limit=payload.limit,
        include_top_comments=payload.include_top_comments,
        comments_limit=payload.comments_limit,
        topic=payload.topic,
        turn=payload.turn,
    )
