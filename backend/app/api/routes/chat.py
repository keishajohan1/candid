from fastapi import APIRouter

from app.models.chat import ChatRequest, ChatResponse
from app.services.claude_service import ClaudeService
from app.services.safety.moderation import ModerationService
from app.utils.prompts import build_educational_prompt

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    moderation = ModerationService()
    safety_result = moderation.precheck(payload.message)
    if not safety_result.allowed:
        return ChatResponse(
            response_text=safety_result.message,
            mode="mock",
            sources=[],
            reflection={
                "notice": "Request blocked by preliminary safety precheck.",
            },
        )

    prompt = build_educational_prompt(payload.message, payload.topic)
    claude_service = ClaudeService()
    result = await claude_service.generate_response(prompt)

    return ChatResponse(
        response_text=result["response_text"],
        mode=result["mode"],
        sources=result.get("sources", []),
        reflection=result.get("reflection", {}),
    )
