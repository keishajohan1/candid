"""Modular prompt skills package — system prompt assembly + chat helpers."""

from app.prompts.builder import build_socratic_system_prompt
from app.prompts.formatters import format_source_block_for_prompt
from app.prompts.user_content import (
    build_socratic_user_content,
    lightweight_sources_for_response,
    source_items_for_prompt_from_ingestion,
)

__all__ = [
    "build_socratic_system_prompt",
    "build_socratic_user_content",
    "format_source_block_for_prompt",
    "lightweight_sources_for_response",
    "source_items_for_prompt_from_ingestion",
]
