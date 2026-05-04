from typing import Any
import time

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

from app.core.config import settings
from app.services.tools import search_verified_knowledge

class ClaudeService:
    """LangChain orchestration for Claude."""

    def __init__(self) -> None:
        self._llm = ChatAnthropic(
            model_name=settings.claude_model,
            temperature=0.35,
            max_tokens=settings.claude_max_output_tokens,
            anthropic_api_key=settings.anthropic_api_key
        )
        self._tools = [search_verified_knowledge]

    async def generate_socratic_response(
        self,
        *,
        system_prompt: str,
        user_content: str,
        history: list[str] = None,
        sources_for_client: list[dict[str, Any]],
    ) -> dict[str, Any]:
        start_time = time.perf_counter()
        
        entity_memory = "Knowledge of user preferences and persistent traits goes here."
        system_content = f"{system_prompt}\n\n[ENTITY MEMORY]: {entity_memory}"
        
        messages = [SystemMessage(content=system_content)]
        
        if history:
            # Truncate history to avoid latency
            recent_history = history[-10:] if len(history) > 10 else history
                
            for msg in recent_history:
                messages.append(HumanMessage(content=msg))
                
        messages.append(HumanMessage(content=user_content))
        
        # --- Native Langchain Tool Calling ---
        llm_with_tools = self._llm.bind_tools(self._tools)
        
        try:
            response = await llm_with_tools.ainvoke(messages)
            tools_used = 0
            
            if response.tool_calls:
                messages.append(response)
                tool_map = {t.name: t for t in self._tools}
                
                for tool_call in response.tool_calls:
                    tool = tool_map.get(tool_call["name"])
                    if tool:
                        tool_msg = await tool.ainvoke(tool_call)
                        messages.append(tool_msg)
                        tools_used += 1
                
                final_response = await self._llm.ainvoke(messages)
                response_text = final_response.content
            else:
                response_text = response.content
        except Exception as e:
            # Fallback handler if native tools fail
            fallback_response = await self._llm.ainvoke(messages)
            response_text = fallback_response.content
            tools_used = 0
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        return {
            "response_text": response_text,
            "mode": "live",
            "sources": sources_for_client,
            "usage": {
                "input_tokens": 0, 
                "output_tokens": 0,
                "latency_ms": latency_ms
            },
            "reflection": {
                "note": "Response orchestrated by native Langchain bind_tools.",
                "tools_used": tools_used
            },
        }
