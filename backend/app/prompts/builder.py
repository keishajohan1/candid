"""Assembles modular prompt skills into the full system prompt."""

from __future__ import annotations

import datetime
from typing import Any

from app.prompts.formatters import (
    build_hard_rules_section,
    build_section_seven_reference,
    format_source_block_for_prompt,
)
from app.prompts.skills.cognitive_protocol import COGNITIVE_PROTOCOL_SKILL
from app.prompts.skills.identity import IDENTITY_SKILL_TEMPLATE
from app.prompts.skills.interaction_model import FIRST_TURN_INTERACTION_SKILL, INTERACTION_MODEL_SKILL
from app.prompts.skills.persona_engine import get_persona_skill
from app.prompts.skills.rag_contract import get_rag_contract_skill
from app.prompts.skills.reddit_handler import REDDIT_HANDLER_SKILL


def _topic_line(topic: str | None, user_message: str = "") -> str:
    if topic and topic.strip():
        return topic.strip()
    if user_message and user_message.strip():
        return user_message.strip()
    return "(No single topic named — infer from the user's message.)"


def build_socratic_system_prompt(
    topic: str | None,
    turn_index: int,
    source_items: list[dict[str, Any]],
    facts: list[str],
    trusted_api_fact_lines: list[str] | None = None,
    history: list[str] | None = None,
    user_message: str = "",
) -> str:
    """Compose conditional skill sections — legacy numbering preserved via rag_contract."""
    _ = history  # reserved for chat route compatibility

    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z").strip()
    tl = _topic_line(topic, user_message=user_message)

    if turn_index == 0:
        tier2_items: list[dict[str, Any]] = []
    else:
        tier2_items = source_items[:3]

    idx = 1
    excerpts_block = format_source_block_for_prompt(tier2_items, start_idx=idx)
    idx += len(tier2_items)

    rag_body = get_rag_contract_skill(facts, trusted_api_fact_lines, idx_start=idx)

    sections: list[str] = []

    sections.append(IDENTITY_SKILL_TEMPLATE.format(current_date=current_date, topic_line=tl))
    sections.append(rag_body)

    if turn_index == 0:
        sections.append(FIRST_TURN_INTERACTION_SKILL)
    else:
        sections.append(INTERACTION_MODEL_SKILL)
        sections.append(COGNITIVE_PROTOCOL_SKILL)

    if turn_index >= 3:
        sections.append(get_persona_skill(turn_index))

    sections.append(build_hard_rules_section(excerpts_block))

    inject_reddit = bool(tier2_items) and turn_index > 0
    if inject_reddit:
        sections.append(REDDIT_HANDLER_SKILL)

    sections.append(build_section_seven_reference())

    return "\n\n".join(s.strip() for s in sections if s.strip())
