from fastapi import APIRouter, Query

from app.models.ingest import IngestResponse
from app.services.scrapers.reddit_service import RedditIngestionService

router = APIRouter()


@router.get("/social-data", response_model=IngestResponse)
async def get_social_data(
    topic: str = Query(default="", max_length=200),
    turn: int = Query(default=0, ge=0, le=10_000),
    q: str | None = Query(default=None, max_length=200),
) -> IngestResponse:
    """
    Reddit sample for a topic; `turn` rotates Reddit sort/subreddit mix.
    """
    search_q = (q or topic or "world news").strip()
    t = topic.strip() or search_q

    reddit_service = RedditIngestionService()
    return await reddit_service.search(
        query=search_q,
        topic=t,
        turn=turn,
        limit=25,
        include_top_comments=False,
        comments_limit=5,
    )
