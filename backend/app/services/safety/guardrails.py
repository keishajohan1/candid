import logging
from typing import Any

from anthropic import AsyncAnthropic

from app.core.config import settings
from app.models.source_content import SourceContent

logger = logging.getLogger(__name__)


class GuardrailsService:
    """Pre-processing pipeline to classify excerpts and scrub PII before main prompt."""

    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def apply_excerpt_guardrails(self, items: list[SourceContent]) -> list[SourceContent]:
        """
        Classifies and scrubs PII from the top excerpts before they reach the main prompt.
        Because this is an LLM call, we run it efficiently on the selected subset.
        """
        if not items:
            return []

        # Anonymize all authors unconditionally at the pipeline level
        for item in items:
            item.author = "[ANONYMIZED USER]"

        prompt = (
            "Review these excerpts. For each, classify the content as [Argument, Testimony, Cited Claim, or Consensus]. "
            "Also, if the excerpt reads like a personal Testimony, redact any specific names and locations "
            "with [REDACTED]. Keep the rest of the text intact.\n\n"
        )

        for idx, item in enumerate(items):
            text = (item.content_text or "").strip()
            prompt += f"--- Excerpt {idx} ---\n{text}\n\n"

        prompt += "Return the output exactly formatted as:\n0: [Classification] | [Scrubbed Text]\n1: [Classification] | [Scrubbed Text]\n"

        try:
            result = await self._client.messages.create(
                model=settings.claude_model,
                max_tokens=2000,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            )
            
            response_text = result.content[0].text.strip().split("\n")
            
            for line in response_text:
                if ":" in line and "|" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2 and parts[0].strip().isdigit():
                        idx = int(parts[0].strip())
                        if idx < len(items):
                            classification, scrubbed_text = parts[1].split("|", 1)
                            items[idx].content_classification = classification.strip()
                            items[idx].content_text = scrubbed_text.strip()
                            
        except Exception as exc:
            logger.warning("Guardrails LLM check failed; falling back to basic anonymization: %s", exc)
            # Basic fallback: author is already scrubbed, default classification to Argument
            for item in items:
                item.content_classification = "Argument"

        return items
