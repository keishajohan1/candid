from dataclasses import dataclass

from app.core.config import settings


@dataclass
class ModerationResult:
    allowed: bool
    message: str = ""


class ModerationService:
    """
    Starter safety precheck.
    This is intentionally simple and acts as a seam for a richer policy engine.
    """

    def precheck(self, user_text: str) -> ModerationResult:
        if not settings.enable_safety_filter:
            return ModerationResult(allowed=True)

        blocked_keywords = {"kill", "bomb", "self-harm"}
        lowered = user_text.lower()
        if any(keyword in lowered for keyword in blocked_keywords):
            return ModerationResult(
                allowed=False,
                message=(
                    "I can not help with harmful requests. "
                    "If you are exploring a sensitive topic academically, "
                    "please reframe your question in a high-level educational way."
                ),
            )
        return ModerationResult(allowed=True)
