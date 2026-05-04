"""Three-stage guardrails: input (rules), excerpts (LLM), output (rules)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from anthropic import AsyncAnthropic

from app.core.config import settings
from app.models.source_content import SourceContent

logger = logging.getLogger(__name__)

_HARM_TRIGGERS = [
    "how to kill",
    "how to make a bomb",
    "how to hurt",
    "i want to hurt",
    "suicide method",
    "how to attack",
]

_CLASSIFIED_TRIGGERS = [
    "classified information",
    "i have inside information",
    "government source told me",
    "leaked document",
]

_PII_PATTERNS = [
    r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",
    r"\b[\w.-]+@[\w.-]+\.\w+\b",
    r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
]

_POLITICAL_LEAN_SIGNALS = [
    "you should vote",
    "the right answer is",
    "clearly the correct position",
    "obviously true that",
]


@dataclass
class GuardrailResult:
    """Result of Stage 1 — input guardrails."""

    action: str  # pass | sanitize | block
    original: str
    sanitized: str
    flags: list[str] = field(default_factory=list)
    block_reason: str | None = None


_INPUT_BLOCK_USER_MESSAGES = {
    "harm_intent": (
        "I cannot help with requests that indicate intent to harm yourself or others. "
        "If you are in crisis, please contact local emergency services or a crisis helpline."
    ),
    "empty_input": "Please send a slightly longer message so we can respond meaningfully.",
}


class GuardrailsService:
    """Stage 1 (rules), Stage 2 (LLM excerpt labeling), Stage 3 (output rules)."""

    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # --- Stage 1: input guardrails -------------------------------------------------

    def apply_input_guardrails(self, user_message: str) -> GuardrailResult:
        """Rule-based checks on raw user input before ingestion or the main model."""
        original = user_message
        flags: list[str] = []

        if len(user_message.strip()) < 3:
            return GuardrailResult(
                action="block",
                original=original,
                sanitized=user_message,
                flags=["too_short"],
                block_reason="empty_input",
            )

        lowered = user_message.lower()
        if any(t in lowered for t in _HARM_TRIGGERS):
            return GuardrailResult(
                action="block",
                original=original,
                sanitized=user_message,
                flags=["harm_intent"],
                block_reason="harm_intent",
            )

        action = "pass"
        sanitized = user_message

        if any(t in lowered for t in _CLASSIFIED_TRIGGERS):
            flags.append("classified_claim")
            action = "sanitize"
            sanitized = self._strip_classified_framing(sanitized)

        for pattern in _PII_PATTERNS:
            if re.search(pattern, sanitized):
                flags.append("pii_detected")
                action = "sanitize"
                sanitized = re.sub(pattern, "[REDACTED]", sanitized)

        return GuardrailResult(
            action=action,
            original=original,
            sanitized=sanitized,
            flags=flags,
            block_reason=None,
        )

    def blocked_response_message(self, block_reason: str | None) -> str:
        """User-visible copy when Stage 1 blocks."""
        key = block_reason or "harm_intent"
        return _INPUT_BLOCK_USER_MESSAGES.get(key, _INPUT_BLOCK_USER_MESSAGES["harm_intent"])

    def _strip_classified_framing(self, text: str) -> str:
        out = text
        lowered = out.lower()
        for phrase in _CLASSIFIED_TRIGGERS:
            while phrase in lowered:
                idx = lowered.index(phrase)
                out = out[:idx] + "[GENERAL DISCUSSION]" + out[idx + len(phrase) :]
                lowered = out.lower()
        return out.strip()

    # --- Stage 2: excerpt guardrails (LLM) ----------------------------------------

    async def apply_excerpt_guardrails(self, items: list[SourceContent]) -> list[SourceContent]:
        """Classify excerpts, flag bias/misinformation risk, scrub PII before main prompt."""
        if not items:
            return []

        items = items[:5]

        for item in items:
            item.author = "[ANONYMIZED USER]"

        prompt = (
            "Review these excerpts. For each, classify the content as "
            "[Argument, Testimony, Cited Claim, or Consensus]. "
            "Also, if the excerpt reads like a personal Testimony, redact any specific names and locations "
            "with [REDACTED]. Keep the rest of the text intact.\n\n"
            "Additionally, for each excerpt flag if:\n"
            "- BIAS_RISK: the excerpt contains strong ideological framing that could push the user toward "
            "a political conclusion without them realizing it\n"
            "- MISINFORMATION_RISK: the excerpt contains a factual claim that is presented as established "
            "fact but is contested or unverifiable\n\n"
        )

        for idx, item in enumerate(items):
            text = (item.content_text or "").strip()
            prompt += f"--- Excerpt {idx} ---\n{text}\n\n"

        prompt += (
            "Return the output exactly formatted as:\n"
            "0: [Classification] | [BIAS_RISK: yes/no] | [MISINFO_RISK: yes/no] | [Scrubbed Text]\n"
            "1: [Classification] | [BIAS_RISK: yes/no] | [MISINFO_RISK: yes/no] | [Scrubbed Text]\n"
            "(continue for each excerpt index).\n"
        )

        try:
            result = await self._client.messages.create(
                model=settings.claude_model,
                max_tokens=300,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            )

            response_lines = result.content[0].text.strip().split("\n")

            for line in response_lines:
                parsed = self._parse_excerpt_guardrail_line(line)
                if parsed is None:
                    continue
                idx, classification, bias_risk, misinfo_risk, scrubbed = parsed
                if idx < len(items):
                    items[idx].content_classification = classification.strip()
                    items[idx].content_text = scrubbed.strip()
                    items[idx].bias_risk = bias_risk
                    items[idx].misinformation_risk = misinfo_risk

        except Exception as exc:
            logger.warning("Guardrails LLM check failed; falling back to basic anonymization: %s", exc)
            for item in items:
                item.content_classification = item.content_classification or "Argument"
                item.bias_risk = False
                item.misinformation_risk = False

        return items

    def _parse_excerpt_guardrail_line(self, line: str) -> tuple[int, str, bool, bool, str] | None:
        """Parse Stage 2 LLM line; supports legacy two-column format."""
        raw = line.strip()
        if ":" not in raw or "|" not in raw:
            return None

        m_full = re.match(
            r"^(\d+)\s*:\s*(.+?)\s*\|\s*\[?\s*BIAS_RISK\s*:\s*(yes|no)\s*\]?\s*\|\s*\[?\s*MISINFO_RISK\s*:\s*(yes|no)\s*\]?\s*\|\s*(.*)$",
            raw,
            re.IGNORECASE | re.DOTALL,
        )
        if m_full:
            idx = int(m_full.group(1))
            classification = m_full.group(2).strip()
            bias_risk = m_full.group(3).lower() == "yes"
            misinfo_risk = m_full.group(4).lower() == "yes"
            scrubbed = m_full.group(5).strip()
            return idx, classification, bias_risk, misinfo_risk, scrubbed

        # Legacy: "0: Argument | scrubbed text"
        m_legacy = re.match(r"^(\d+)\s*:\s*(.+?)\s*\|\s*(.+)$", raw)
        if m_legacy:
            idx = int(m_legacy.group(1))
            left = m_legacy.group(2).strip()
            right = m_legacy.group(3).strip()
            return idx, left, False, False, right

        return None

    # --- Stage 3: output guardrails -----------------------------------------------

    def apply_output_guardrails(self, response_text: str) -> str:
        """Rule-based checks on assistant output before it reaches the client."""
        text = response_text

        lowered = text.lower()
        for signal in _POLITICAL_LEAN_SIGNALS:
            if signal in lowered:
                logger.warning(
                    "Output guardrail: potential opinion leak detected: '%s'",
                    signal,
                )

        question_count = text.count("?")
        if question_count > 2:
            logger.warning(
                "Output guardrail: assistant produced %d questions, expected ~1",
                question_count,
            )

        if "u/" in text.lower() or "reddit.com/user" in lowered:
            text = re.sub(r"(?i)u/\w+", "[ANONYMIZED]", text)
            text = re.sub(r"https?://(?:www\.)?reddit\.com/user/\w+", "[ANONYMIZED]", text)
            logger.warning("Output guardrail: Reddit username pattern found in response, redacted")

        return text
