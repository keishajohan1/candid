import asyncio
import time
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.core.config import settings
from app.services.tools import search_verified_knowledge


class ClaudeService:
    """LangChain orchestration for Claude."""

    def __init__(self) -> None:
        self._llm = ChatAnthropic(
            model_name=settings.claude_model,
            temperature=0.35,
            max_tokens=settings.claude_max_output_tokens,
            anthropic_api_key=settings.anthropic_api_key,
        )
        self._tools = [search_verified_knowledge]

    async def generate_socratic_response(
        self,
        *,
        system_prompt: str,
        user_content: str,
        history: list[str] = None,
        sources_for_client: list[dict[str, Any]],
        allow_verified_knowledge_tool: bool = True,
    ) -> dict[str, Any]:
        start_time = time.perf_counter()

        entity_memory = "Knowledge of user preferences and persistent traits goes here."
        system_content = f"{system_prompt}\n\n[ENTITY MEMORY]: {entity_memory}"

        messages = [SystemMessage(content=system_content)]

        if history:
            recent_history = history[-10:] if len(history) > 10 else history

            for msg in recent_history:
                messages.append(HumanMessage(content=msg))

        messages.append(HumanMessage(content=user_content))

        tools_used = 0
        note = "Response orchestrated by native Langchain bind_tools."

        try:
            if not allow_verified_knowledge_tool:
                note = (
                    "Single completion without KB tool: Tier 1A facts already present in the system prompt."
                )
                response = await self._llm.ainvoke(messages)
                response_text = response.content
            else:
                llm_with_tools = self._llm.bind_tools(self._tools)
                response = await llm_with_tools.ainvoke(messages)

                if response.tool_calls:
                    messages.append(response)
                    tool_map = {t.name: t for t in self._tools}

                    async def _invoke_one(tool_call: dict[str, Any]) -> ToolMessage | None:
                        tool = tool_map.get(tool_call["name"])
                        if tool:
                            return await tool.ainvoke(tool_call)
                        return None

                    tool_messages = await asyncio.gather(
                        *(_invoke_one(tc) for tc in response.tool_calls)
                    )
                    for tm in tool_messages:
                        if tm is not None:
                            messages.append(tm)
                    tools_used = sum(1 for tm in tool_messages if tm is not None)

                    final_response = await self._llm.ainvoke(messages)
                    response_text = final_response.content
                else:
                    response_text = response.content
        except Exception:
            fallback_response = await self._llm.ainvoke(messages)
            response_text = fallback_response.content
            tools_used = 0
            note = "Fallback: native tools path failed; plain completion used."

        latency_ms = (time.perf_counter() - start_time) * 1000

        return {
            "response_text": response_text,
            "mode": "live",
            "sources": sources_for_client,
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "latency_ms": latency_ms,
            },
            "reflection": {
                "note": note,
                "tools_used": tools_used,
            },
        }
