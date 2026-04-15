import logging
from typing import Any

from fastapi import APIRouter

from app.models.chat import ChatRequest, ChatResponse
from app.services.claude_service import ClaudeService
from app.services.ingestion.rerank_bm25 import rerank_source_contents_by_query
from app.services.knowledge_base import get_verified_facts_for_topic, has_static_kb_for_topic
from app.services.safety.guardrails import GuardrailsService
from app.services.safety.moderation import ModerationService
from app.services.scrapers.reddit_service import RedditIngestionService
from app.services.trusted_data import TrustedFactsOrchestrator
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
    trusted_api_lines: list[str] = []
    trusted_debug: dict[str, Any] = {}

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
            reddit_items = rerank_source_contents_by_query(reddit_items, q)
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
    
    topic_search = payload.topic or payload.message
    facts = get_verified_facts_for_topic(topic_search)

    if not has_static_kb_for_topic(topic_search):
        try:
            orch = TrustedFactsOrchestrator()
            trusted_api_lines, trusted_refs, trusted_debug = await orch.build_trusted_facts(
                topic=payload.topic,
                message=payload.message,
            )
            sources_out.extend(trusted_refs)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Trusted API orchestration failed: %s", exc)
            trusted_debug = {"trusted_api_error": str(exc)}
    else:
        trusted_debug = {"trusted_api_skipped": True, "trusted_api_reason": "static_kb_matched"}

    import re

    for fact in facts:
        match = re.search(r"\(([^)]+)\)\.$", fact.strip())
        if match:
            sources_out.append(
                {
                    "source": "knowledge_base",
                    "label": match.group(1),
                    "url": None,
                }
            )

    system_prompt = build_socratic_system_prompt(
        topic=payload.topic,
        turn_index=payload.turn_index,
        history=payload.history,
        source_items=prompt_items,
        facts=facts,
        trusted_api_fact_lines=trusted_api_lines,
    )
    user_content = build_socratic_user_content(message=payload.message)

    claude_service = ClaudeService()
    result = await claude_service.generate_socratic_response(
        system_prompt=system_prompt,
        user_content=user_content,
        sources_for_client=sources_out,
    )

    response_text = result["response_text"]
    if "<sources>" in response_text and "</sources>" in response_text:
        main_text, rest = response_text.split("<sources>", 1)
        sources_text, _ = rest.split("</sources>", 1)
        result["response_text"] = main_text.strip()
        
        for line in sources_text.strip().split("\n"):
            line = line.strip()
            if line.startswith("[") and "]" in line:
                label_part = line.split("]", 1)[1].strip()
                if label_part.startswith("-"):
                    label_part = label_part[1:].strip()
                sources_out.append({
                    "source": "Knowledge Base (LLM)",
                    "label": label_part,
                    "url": None
                })
    elif "DYNAMIC_SOURCES:" in response_text:
        main_text, sources_text = response_text.split("DYNAMIC_SOURCES:", 1)
        result["response_text"] = main_text.strip()
        
        for line in sources_text.strip().split("\n"):
            line = line.strip()
            if line.startswith("[") and "]" in line:
                label_part = line.split("]", 1)[1].strip()
                if label_part.startswith("-"):
                    label_part = label_part[1:].strip()
                sources_out.append({
                    "source": "Knowledge Base (LLM)",
                    "label": label_part,
                    "url": None
                })

    debug.update(
        {
            "source_count": len(sources_out),
            "reddit_item_count": len(reddit_items),
            "ingest_errors": ingest_errors,
            "live_claude": True,
            "trusted_api": trusted_debug,
            "static_kb_matched": has_static_kb_for_topic(topic_search),
            "trusted_api_lines_count": len(trusted_api_lines),
        }
    )

    return ChatResponse(
        response_text=result["response_text"],
        mode=result["mode"],
        sources=result.get("sources", sources_out),
        reflection=result.get("reflection", {}),
        debug=debug,
    )
