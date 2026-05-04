"""
Compatibility barrel — canonical implementations live in ``app.prompts``.
Routes may import from ``app.core.prompts`` or ``app.prompts`` interchangeably.
"""

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
