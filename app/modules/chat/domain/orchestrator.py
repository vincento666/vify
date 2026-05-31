from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    HeuristicOpenAIChatClient,
    OpenAIChatRequestBuilder,
)
from app.modules.chat.domain.tool_runner import McpToolExecutor, ToolCallRunner, ToolExecutionResult
from app.modules.chat.domain.tool_schema import ToolDefinition
from app.modules.provider.infra.llm_adapters import OpenAIAdapterParser


@dataclass(frozen=True)
class ChatOrchestrationResult:
    final_content: str
    tool_results: list[ToolExecutionResult]


class ChatOrchestrator:
    def __init__(
        self,
        llm_client: Any | None = None,
        request_builder: OpenAIChatRequestBuilder | None = None,
        parser: OpenAIAdapterParser | None = None,
        tool_runner: ToolCallRunner | None = None,
    ) -> None:
        self._llm_client = llm_client or HeuristicOpenAIChatClient()
        self._request_builder = request_builder or OpenAIChatRequestBuilder()
        self._parser = parser or OpenAIAdapterParser()
        self._tool_runner = tool_runner or ToolCallRunner()

    def run(
        self,
        model: str,
        messages: list[ChatRequestMessage],
        tools: list[ToolDefinition],
        tool_ids: list[int],
        mcp_facade: McpToolExecutor,
        llm_client: Any | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        extra_params: dict[str, Any] | None = None,
    ) -> ChatOrchestrationResult:
        client = llm_client or self._llm_client
        first_payload = self._request_builder.build(
            model=model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_params=extra_params,
        )
        first = self._parser.parse_chat_response(client.complete(first_payload))
        if not first.tool_calls:
            return ChatOrchestrationResult(final_content=first.content, tool_results=[])

        tool_results = self._tool_runner.run_calls(tool_ids, first.tool_calls, mcp_facade)
        second_messages = [
            *messages,
            ChatRequestMessage(
                role="assistant",
                content=first.content or None,
                tool_calls=[
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments),
                        },
                    }
                    for call in first.tool_calls
                ],
            ),
            *[
                ChatRequestMessage(
                    role="tool",
                    content=result.content if result.success else result.error_message,
                    tool_call_id=result.call_id,
                    name=result.name,
                )
                for result in tool_results
            ],
        ]
        second_payload = self._request_builder.build(
            model=model,
            messages=second_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_params=extra_params,
        )
        second = self._parser.parse_chat_response(client.complete(second_payload))
        return ChatOrchestrationResult(final_content=second.content, tool_results=tool_results)
