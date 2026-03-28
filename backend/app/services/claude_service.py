from typing import Any

from anthropic import AsyncAnthropic

from app.core.config import settings


class ClaudeService:
    """Adapter around Anthropic. Retrieval/scraping happens outside this class."""

    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate_socratic_response(
        self,
        *,
        system_prompt: str,
        user_content: str,
        sources_for_client: list[dict[str, Any]],
    ) -> dict[str, Any]:
        result = await self._client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_output_tokens,
            temperature=0.35,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        text_parts: list[str] = []
        for block in result.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
        response_text = "\n".join(text_parts).strip()
        if not response_text:
            raise RuntimeError("Anthropic returned an empty text response")
        return {
            "response_text": response_text,
            "mode": "live",
            "sources": sources_for_client,
            "reflection": {
                "note": "Response from Claude using backend-supplied excerpts only; model did not scrape.",
            },
        }
