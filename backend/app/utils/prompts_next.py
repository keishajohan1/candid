"""Parallel surface — forwards to modular ``app.prompts``."""

from __future__ import annotations

from app.prompts import (
    build_socratic_system_prompt,
    build_socratic_user_content,
    format_source_block_for_prompt,
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
