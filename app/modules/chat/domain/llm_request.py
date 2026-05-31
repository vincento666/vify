from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from app.modules.chat.domain.tool_schema import OpenAIToolSchemaSerializer, ToolDefinition


@dataclass(frozen=True)
class ChatRequestMessage:
    role: str
    content: str


class OpenAIChatRequestBuilder:
    def __init__(self, tool_serializer: OpenAIToolSchemaSerializer | None = None) -> None:
        self._tool_serializer = tool_serializer or OpenAIToolSchemaSerializer()

    def build(
        self,
        model: str,
        messages: list[ChatRequestMessage],
        tools: list[ToolDefinition] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in messages
            ],
        }
        if tools:
            payload["tools"] = self._tool_serializer.serialize(tools)
            payload["tool_choice"] = "auto"
        return payload


class FakeOpenAIChatClient:
    def __init__(
        self,
        response_payload: dict[str, Any] | None = None,
        response_payloads: list[dict[str, Any]] | None = None,
    ) -> None:
        self.captured_payload: dict[str, Any] = {}
        self.captured_payloads: list[dict[str, Any]] = []
        self._response_payload = response_payload
        self._response_payloads = list(response_payloads or [])

    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.captured_payload = payload
        self.captured_payloads.append(payload)
        if self._response_payloads:
            return self._response_payloads.pop(0)
        if self._response_payload is not None:
            return self._response_payload
        return {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"total_tokens": 1},
        }


class HeuristicOpenAIChatClient(FakeOpenAIChatClient):
    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.captured_payload = payload
        self.captured_payloads.append(payload)
        messages = payload.get("messages", [])
        if isinstance(messages, list) and messages:
            last_message = messages[-1]
            if isinstance(last_message, dict) and last_message.get("role") == "tool":
                return _assistant_response(f"Tool answer: {last_message.get('content') or ''}")
            if payload.get("tools"):
                order_id = _extract_order_id(str(last_message.get("content") or ""))
                if order_id:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_lookup_order",
                                            "type": "function",
                                            "function": {
                                                "name": "lookup_order",
                                                "arguments": f'{{"orderId":"{order_id}"}}',
                                            },
                                        }
                                    ],
                                },
                                "finish_reason": "tool_calls",
                            }
                        ],
                        "usage": {"total_tokens": 1},
                    }
        return _assistant_response("ok")


def _extract_order_id(content: str) -> str | None:
    match = re.search(r"\b[A-Z]-\d+\b", content.upper())
    return match.group(0) if match else None


def _assistant_response(content: str) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"total_tokens": max(1, len(content.split()))},
    }
