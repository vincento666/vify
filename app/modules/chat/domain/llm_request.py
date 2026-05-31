from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

import httpx

from app.modules.chat.domain.tool_schema import OpenAIToolSchemaSerializer, ToolDefinition


@dataclass(frozen=True)
class ChatRequestMessage:
    role: str
    content: str | None
    tool_call_id: str | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class ProviderChatConfig:
    provider_type: str
    base_url: str
    auth_config: dict[str, Any]


class OpenAIChatRequestBuilder:
    def __init__(self, tool_serializer: OpenAIToolSchemaSerializer | None = None) -> None:
        self._tool_serializer = tool_serializer or OpenAIToolSchemaSerializer()

    def build(
        self,
        model: str,
        messages: list[ChatRequestMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [_message_payload(message) for message in messages],
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if extra_params:
            payload.update(extra_params)
        if tools:
            payload["tools"] = self._tool_serializer.serialize(tools)
            payload["tool_choice"] = "auto"
        return payload


class ProviderBackedOpenAIChatClient:
    def __init__(self, config: ProviderChatConfig, timeout: float = 60.0) -> None:
        self._config = config
        self._timeout = timeout

    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._config.base_url.startswith("mock://"):
            return _mock_provider_response(payload)

        headers = {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
            "X-Title": "Hify",
        }
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._config.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
        if response.status_code >= 400:
            raise RuntimeError(f"LLM request failed: HTTP {response.status_code} {response.text}")
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("LLM response is not a JSON object")
        return data

    def _api_key(self) -> str:
        return str(self._config.auth_config.get("api_key") or self._config.auth_config.get("apiKey") or "")


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


def _message_payload(message: ChatRequestMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": message.role,
        "content": message.content,
    }
    if message.tool_call_id:
        payload["tool_call_id"] = message.tool_call_id
    if message.name:
        payload["name"] = message.name
    if message.tool_calls:
        payload["tool_calls"] = message.tool_calls
    return payload


def _mock_provider_response(payload: dict[str, Any]) -> dict[str, Any]:
    messages = payload.get("messages", [])
    if isinstance(messages, list) and messages:
        last_message = messages[-1]
        if isinstance(last_message, dict) and last_message.get("role") == "tool":
            return _assistant_response(f"Tool answer: {last_message.get('content') or ''}")
        if payload.get("tools") and isinstance(last_message, dict):
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
                                            "arguments": json.dumps({"orderId": order_id}),
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                    "usage": {"total_tokens": 1},
                }
        if isinstance(last_message, dict):
            return _assistant_response(f"LLM mock: {last_message.get('content') or ''}")
    return _assistant_response("LLM mock: ok")


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
