import logging
from typing import Any

from fastapi import APIRouter

from app.models.chat import ChatRequest, ChatResponse
from app.services.claude_service import ClaudeService
from app.services.knowledge_base import get_verified_facts_for_topic
from app.services.safety.guardrails import GuardrailsService
from app.services.safety.moderation import ModerationService
from app.services.scrapers.reddit_service import RedditIngestionService
from app.utils.prompts import (
    build_socratic_system_prompt,
    build_socratic_user_content,
    lightweight_sources_for_response,
    source_items_for_prompt_from_ingestion,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Reddit: limit for post search; comment fetches disabled by default (see RedditIngestionService)
_CHAT_REDDIT_LIMIT = 25


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    moderation = ModerationService()
    safety_result = moderation.precheck(payload.message)
    if not safety_result.allowed:
        return ChatResponse(
            response_text=safety_result.message,
            mode="blocked",
            sources=[],
            reflection={"notice": "Request blocked by preliminary safety precheck."},
            debug={"blocked": True},
        )

    debug: dict[str, Any] = {
        "turn_index": payload.turn_index,
        "fetch_sources": payload.fetch_sources,
    }

    reddit_items: list[Any] = []
    ingest_errors: list[dict[str, Any]] = []

    if payload.fetch_sources:
        q = (payload.source_query or payload.topic or payload.message[:120]).strip()
        debug["ingestion_query"] = q

        try:
            reddit = RedditIngestionService()
            r_result = await reddit.search(
                query=q,
                topic=(payload.topic or "").strip(),
                turn=payload.turn_index,
                limit=_CHAT_REDDIT_LIMIT,
                include_top_comments=False,
                comments_limit=5,
            )
            reddit_items = list(r_result.items)
            for e in r_result.errors:
                ingest_errors.append({"source": "reddit", "code": e.code, "message": e.message})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Reddit ingestion in chat failed: %s", exc)
            ingest_errors.append({"source": "reddit", "code": "exception", "message": str(exc)})

        if reddit_items:
            try:
                guardrails = GuardrailsService()
                reddit_items[:5] = await guardrails.apply_excerpt_guardrails(reddit_items[:5])
            except Exception as exc:
                logger.warning("Guardrails service failed inline: %s", exc)

    prompt_items = source_items_for_prompt_from_ingestion(reddit_items)
    sources_out = lightweight_sources_for_response(prompt_items)
    
    facts = get_verified_facts_for_topic(payload.topic)

    system_prompt = build_socratic_system_prompt(
        topic=payload.topic,
        turn_index=payload.turn_index,
        history=payload.history,
        source_items=prompt_items,
        facts=facts,
    )
    user_content = build_socratic_user_content(message=payload.message)

    claude_service = ClaudeService()
    result = await claude_service.generate_socratic_response(
        system_prompt=system_prompt,
        user_content=user_content,
        sources_for_client=sources_out,
    )

    debug.update(
        {
            "source_count": len(sources_out),
            "reddit_item_count": len(reddit_items),
            "ingest_errors": ingest_errors,
            "live_claude": True,
        }
    )

    return ChatResponse(
        response_text=result["response_text"],
        mode=result["mode"],
        sources=result.get("sources", sources_out),
        reflection=result.get("reflection", {}),
        debug=debug,
    )
