import logging
from typing import Any

try:
    from anthropic import AsyncAnthropic  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - depends on local interpreter setup
    AsyncAnthropic = None  # type: ignore[assignment]

from app.core.config import settings

logger = logging.getLogger(__name__)


class ClaudeService:
    """Adapter around Anthropic for Candid chat responses."""

    def __init__(self) -> None:
        self._enabled = bool(settings.anthropic_api_key.strip()) and AsyncAnthropic is not None
        self._client = (
            AsyncAnthropic(api_key=settings.anthropic_api_key) if self._enabled else None
        )

    async def generate_response(self, prompt: str) -> dict[str, Any]:
        if not self._enabled or self._client is None:
            return self._mock_response()

        try:
            result = await self._client.messages.create(
                model=settings.claude_model,
                max_tokens=700,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            text_parts = []
            for block in result.content:
                if getattr(block, "type", None) == "text":
                    text_parts.append(block.text)
            response_text = "\n".join(text_parts).strip() or self._mock_response()[
                "response_text"
            ]
            return {
                "response_text": response_text,
                "mode": "live",
                "sources": [],
                "reflection": {
                    "note": "Live Claude response returned without source attachment in MVP scaffold."
                },
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception("Claude request failed; falling back to mock response: %s", exc)
            return self._mock_response()

    @staticmethod
    def _mock_response() -> dict[str, Any]:
        return {
            "response_text": (
                "I do not have a configured Claude key in this environment yet. "
                "For now, I can still help by outlining neutral perspectives, "
                "questions to investigate, and source types to consult."
            ),
            "mode": "mock",
            "sources": [
                {
                    "type": "placeholder",
                    "title": "No live sources configured",
                    "url": None,
                }
            ],
            "reflection": {
                "confidence": "low",
                "next_step": "Set ANTHROPIC_API_KEY for live model responses.",
            },
        }
