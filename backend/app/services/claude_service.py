import logging
from typing import Any

try:
    from anthropic import AsyncAnthropic  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - depends on local interpreter setup
    AsyncAnthropic = None  # type: ignore[assignment]

from app.core.config import settings

logger = logging.getLogger(__name__)


class ClaudeService:
    """Adapter around Anthropic. Retrieval/scraping happens outside this class."""

    def __init__(self) -> None:
        self._enabled = settings.has_claude_key() and AsyncAnthropic is not None
        key = settings.anthropic_api_key or ""
        self._client = AsyncAnthropic(api_key=key) if self._enabled else None

    async def generate_socratic_response(
        self,
        *,
        system_prompt: str,
        user_content: str,
        sources_for_client: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self._enabled or self._client is None:
            return self._mock_socratic_response(sources_for_client=sources_for_client)

        try:
            result = await self._client.messages.create(
                model=settings.claude_model,
                max_tokens=500,
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
                return self._mock_socratic_response(sources_for_client=sources_for_client)
            return {
                "response_text": response_text,
                "mode": "live",
                "sources": sources_for_client,
                "reflection": {
                    "note": "Response from Claude using backend-supplied excerpts only; model did not scrape.",
                },
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception("Claude request failed; falling back to mock: %s", exc)
            return self._mock_socratic_response(sources_for_client=sources_for_client)

    @staticmethod
    def _mock_socratic_response(
        sources_for_client: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Structured like live mode: short, one question, no agreement — no API key required."""
        has_sources = bool(sources_for_client)
        if has_sources:
            body = (
                "Without endorsing any side: the excerpts you were given pull in more than one direction. "
                "What single claim are you willing to stake your argument on, and what would falsify it?"
            )
        else:
            body = (
                "You stated a position without tying it to a testable claim. "
                "What is the weakest part of your own argument — and why haven't you addressed it yet?"
            )
        return {
            "response_text": body,
            "mode": "mock",
            "sources": sources_for_client
            or [
                {
                    "source": "system",
                    "label": "No excerpts (mock mode or fetch_sources=false)",
                    "url": None,
                }
            ],
            "reflection": {
                "reason": "ANTHROPIC_API_KEY missing, Claude unavailable, or request error.",
                "next_step": "Set ANTHROPIC_API_KEY in .env (repo root) for live Socratic responses.",
            },
        }
