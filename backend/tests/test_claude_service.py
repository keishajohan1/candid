"""Tests for ClaudeService tool path vs single-completion path."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from app.services.claude_service import ClaudeService


@pytest.mark.asyncio
async def test_generate_skips_bind_tools_when_kb_tool_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_llm = MagicMock()
    mock_llm.bind_tools = MagicMock(side_effect=AssertionError("bind_tools must not be called"))
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="direct answer"))

    monkeypatch.setattr("app.services.claude_service.ChatAnthropic", lambda **kwargs: mock_llm)

    svc = ClaudeService()
    out = await svc.generate_socratic_response(
        system_prompt="sys",
        user_content="user",
        sources_for_client=[],
        allow_verified_knowledge_tool=False,
    )

    assert out["response_text"] == "direct answer"
    assert out["reflection"]["tools_used"] == 0
    assert "Tier 1A facts already present" in out["reflection"]["note"]
    mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_generate_bind_tools_path_no_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_llm = MagicMock()
    mock_bound = MagicMock()
    mock_bound.ainvoke = AsyncMock(return_value=AIMessage(content="no tools"))
    mock_llm.bind_tools = MagicMock(return_value=mock_bound)
    mock_llm.ainvoke = AsyncMock()

    monkeypatch.setattr("app.services.claude_service.ChatAnthropic", lambda **kwargs: mock_llm)

    svc = ClaudeService()
    out = await svc.generate_socratic_response(
        system_prompt="s",
        user_content="u",
        sources_for_client=[],
        allow_verified_knowledge_tool=True,
    )

    assert out["response_text"] == "no tools"
    assert out["reflection"]["tools_used"] == 0
    mock_bound.ainvoke.assert_called_once()
    mock_llm.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_generate_parallel_tool_messages_then_final(monkeypatch: pytest.MonkeyPatch) -> None:
    tc1 = {"name": "search_verified_knowledge", "args": {"query": "a"}, "id": "id-1"}
    tc2 = {"name": "search_verified_knowledge", "args": {"query": "b"}, "id": "id-2"}
    first = AIMessage(content="", tool_calls=[tc1, tc2])

    mock_tool = MagicMock()
    mock_tool.name = "search_verified_knowledge"
    mock_tool.ainvoke = AsyncMock(
        side_effect=[
            ToolMessage(content="facts a", tool_call_id="id-1"),
            ToolMessage(content="facts b", tool_call_id="id-2"),
        ]
    )

    mock_llm = MagicMock()
    mock_bound = MagicMock()
    mock_bound.ainvoke = AsyncMock(return_value=first)
    mock_llm.bind_tools = MagicMock(return_value=mock_bound)
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="final synthesis"))

    monkeypatch.setattr("app.services.claude_service.ChatAnthropic", lambda **kwargs: mock_llm)

    svc = ClaudeService()
    svc._tools = [mock_tool]

    out = await svc.generate_socratic_response(
        system_prompt="s",
        user_content="u",
        sources_for_client=[],
        allow_verified_knowledge_tool=True,
    )

    assert out["response_text"] == "final synthesis"
    assert out["reflection"]["tools_used"] == 2
    assert mock_tool.ainvoke.await_count == 2
    mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_generate_fallback_on_tool_path_error(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_llm = MagicMock()
    mock_bound = MagicMock()
    mock_bound.ainvoke = AsyncMock(side_effect=RuntimeError("tool bind failed"))
    mock_llm.bind_tools = MagicMock(return_value=mock_bound)
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="fallback text"))

    monkeypatch.setattr("app.services.claude_service.ChatAnthropic", lambda **kwargs: mock_llm)

    svc = ClaudeService()
    out = await svc.generate_socratic_response(
        system_prompt="s",
        user_content="u",
        sources_for_client=[],
        allow_verified_knowledge_tool=True,
    )

    assert out["response_text"] == "fallback text"
    assert out["reflection"]["tools_used"] == 0
    assert "Fallback" in out["reflection"]["note"]
