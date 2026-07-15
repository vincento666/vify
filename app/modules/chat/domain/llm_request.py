from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import json
import os
import re
from threading import BoundedSemaphore, Lock
from time import sleep
from typing import Any, Callable

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


_ASYNC_STREAM_LIMITERS: dict[tuple[str, str, str, int], BoundedSemaphore] = {}
_ASYNC_STREAM_LIMITERS_LOCK = Lock()


def _shared_async_stream_limiter(
    config: ProviderChatConfig,
    *,
    max_concurrent_streams: int,
) -> BoundedSemaphore:
    auth_identity = str(
        config.auth_config.get("api_key_ref")
        or config.auth_config.get("apiKeyRef")
        or config.auth_config.get("api_key")
        or config.auth_config.get("apiKey")
        or ""
    )
    key = (
        str(config.provider_type or "").upper(),
        str(config.base_url or "").rstrip("/"),
        hashlib.sha256(auth_identity.encode()).hexdigest(),
        max(1, max_concurrent_streams),
    )
    with _ASYNC_STREAM_LIMITERS_LOCK:
        limiter = _ASYNC_STREAM_LIMITERS.get(key)
        if limiter is None:
            limiter = BoundedSemaphore(max_concurrent_streams)
            _ASYNC_STREAM_LIMITERS[key] = limiter
        return limiter


async def _acquire_async_stream_limiter(limiter: BoundedSemaphore) -> None:
    while not limiter.acquire(blocking=False):
        await asyncio.sleep(0.01)


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
            payload["tool_choice"] = payload.get("tool_choice", "auto")
        return payload


class ProviderBackedOpenAIChatClient:
    def __init__(
        self,
        config: ProviderChatConfig,
        timeout: float = 60.0,
        max_attempts: int = 3,
        retry_sleep: float = 0.5,
        max_concurrent_streams: int = 4,
    ) -> None:
        self._config = config
        self._timeout = timeout
        self._max_attempts = max(1, max_attempts)
        self._retry_sleep = max(0.0, retry_sleep)
        self._async_stream_limiter = _shared_async_stream_limiter(
            config,
            max_concurrent_streams=max(1, max_concurrent_streams),
        )

    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._config.base_url.startswith("mock://"):
            return _mock_provider_response(payload)

        headers = {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
            "X-Title": "Hify",
        }
        response = self._post_with_retry(headers, payload)
        if response.status_code >= 400:
            raise RuntimeError(f"LLM request failed: HTTP {response.status_code} {response.text}")
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("LLM response is not a JSON object")
        return data

    def stream_complete(
        self,
        payload: dict[str, Any],
        on_delta: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        if self._config.base_url.startswith("mock://"):
            response = _mock_provider_response(payload)
            content = str(_first_choice_message(response).get("content") or "")
            if on_delta and content:
                on_delta(content)
            return response

        headers = {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
            "X-Title": "Hify",
        }
        stream_payload = {
            **payload,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        return self._stream_with_retry(headers, stream_payload, on_delta)

    async def stream_complete_async(
        self,
        payload: dict[str, Any],
        on_delta: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Consume a provider SSE stream without blocking the caller's event loop."""
        if self._config.base_url.startswith("mock://"):
            return self.stream_complete(payload, on_delta=on_delta)
        headers = {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
            "X-Title": "Hify",
        }
        stream_payload = {
            **payload,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        await _acquire_async_stream_limiter(self._async_stream_limiter)
        try:
            return await self._async_stream_with_retry(headers, stream_payload, on_delta)
        finally:
            self._async_stream_limiter.release()

    def _api_key(self) -> str:
        direct = str(self._config.auth_config.get("api_key") or self._config.auth_config.get("apiKey") or "")
        if direct:
            return direct
        ref = str(self._config.auth_config.get("api_key_ref") or self._config.auth_config.get("apiKeyRef") or "")
        if ref.startswith("env:"):
            return os.getenv(ref.removeprefix("env:"), "")
        return ""

    def _post_with_retry(self, headers: dict[str, str], payload: dict[str, Any]) -> httpx.Response:
        last_error: httpx.TransportError | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                with httpx.Client(timeout=self._timeout, trust_env=True) as client:
                    return client.post(
                        f"{self._config.base_url.rstrip('/')}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
            except httpx.TransportError as exc:
                last_error = exc
                if attempt >= self._max_attempts:
                    raise
                if self._retry_sleep:
                    sleep(self._retry_sleep)
        raise last_error or RuntimeError("LLM request failed before a response was returned")

    def _stream_with_retry(
        self,
        headers: dict[str, str],
        payload: dict[str, Any],
        on_delta: Callable[[str], None] | None,
    ) -> dict[str, Any]:
        last_error: httpx.TransportError | None = None
        for attempt in range(1, self._max_attempts + 1):
            emitted_visible_delta = False

            def deliver_delta(content: str) -> None:
                nonlocal emitted_visible_delta
                emitted_visible_delta = True
                if on_delta is not None:
                    on_delta(content)

            try:
                return self._stream_once(headers, payload, deliver_delta)
            except httpx.TransportError as exc:
                last_error = exc
                if emitted_visible_delta or attempt >= self._max_attempts:
                    raise
                if self._retry_sleep:
                    sleep(self._retry_sleep)
        raise last_error or RuntimeError("LLM stream failed before a response was returned")

    def _stream_once(
        self,
        headers: dict[str, str],
        payload: dict[str, Any],
        on_delta: Callable[[str], None] | None,
    ) -> dict[str, Any]:
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_calls: dict[int, dict[str, Any]] = {}
        usage: dict[str, Any] = {}
        finish_reason = "stop"
        with httpx.Client(timeout=self._timeout, trust_env=True) as client:
            with client.stream(
                "POST",
                f"{self._config.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    raise RuntimeError(f"LLM request failed: HTTP {response.status_code} {response.read().decode()}")
                for line in response.iter_lines():
                    event = _stream_json_event(line)
                    if event is None:
                        continue
                    event_usage = event.get("usage")
                    if isinstance(event_usage, dict):
                        usage = event_usage
                    for choice in event.get("choices") or []:
                        if not isinstance(choice, dict):
                            continue
                        finish_reason = str(choice.get("finish_reason") or finish_reason)
                        raw_delta = choice.get("delta")
                        delta: dict[str, Any] = raw_delta if isinstance(raw_delta, dict) else {}
                        content = delta.get("content")
                        if isinstance(content, str) and content:
                            content_parts.append(content)
                            if on_delta:
                                on_delta(content)
                        reasoning = _delta_reasoning_text(delta)
                        if reasoning:
                            reasoning_parts.append(reasoning)
                        _accumulate_tool_call_deltas(tool_calls, delta.get("tool_calls"))
        message: dict[str, Any] = {
            "role": "assistant",
            "content": "".join(content_parts) or None,
        }
        if reasoning_parts:
            reasoning = "".join(reasoning_parts)
            message["reasoning"] = reasoning
            message["reasoning_details"] = [{"type": "reasoning.text", "text": reasoning}]
        if tool_calls:
            message["tool_calls"] = [_complete_tool_call(tool_calls[index]) for index in sorted(tool_calls)]
        return {
            "choices": [{"message": message, "finish_reason": finish_reason}],
            "usage": usage,
        }

    async def _async_stream_with_retry(
        self,
        headers: dict[str, str],
        payload: dict[str, Any],
        on_delta: Callable[[str], None] | None,
    ) -> dict[str, Any]:
        last_error: httpx.TransportError | None = None
        for attempt in range(1, self._max_attempts + 1):
            emitted_visible_delta = False

            def deliver_delta(content: str) -> None:
                nonlocal emitted_visible_delta
                emitted_visible_delta = True
                if on_delta is not None:
                    on_delta(content)

            try:
                return await self._async_stream_once(headers, payload, deliver_delta)
            except httpx.TransportError as exc:
                last_error = exc
                if emitted_visible_delta or attempt >= self._max_attempts:
                    raise
                if self._retry_sleep:
                    await asyncio.sleep(self._retry_sleep)
        raise last_error or RuntimeError("LLM async stream failed before a response was returned")

    async def _async_stream_once(
        self,
        headers: dict[str, str],
        payload: dict[str, Any],
        on_delta: Callable[[str], None] | None,
    ) -> dict[str, Any]:
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_calls: dict[int, dict[str, Any]] = {}
        usage: dict[str, Any] = {}
        finish_reason = "stop"
        async with httpx.AsyncClient(timeout=self._timeout, trust_env=True) as client:
            async with client.stream(
                "POST",
                f"{self._config.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    body = (await response.aread()).decode()
                    raise RuntimeError(f"LLM request failed: HTTP {response.status_code} {body}")
                async for line in response.aiter_lines():
                    event = _stream_json_event(line)
                    if event is None:
                        continue
                    event_usage = event.get("usage")
                    if isinstance(event_usage, dict):
                        usage = event_usage
                    for choice in event.get("choices") or []:
                        if not isinstance(choice, dict):
                            continue
                        finish_reason = str(choice.get("finish_reason") or finish_reason)
                        raw_delta = choice.get("delta")
                        delta: dict[str, Any] = raw_delta if isinstance(raw_delta, dict) else {}
                        content = delta.get("content")
                        if isinstance(content, str) and content:
                            content_parts.append(content)
                            if on_delta:
                                on_delta(content)
                        reasoning = _delta_reasoning_text(delta)
                        if reasoning:
                            reasoning_parts.append(reasoning)
                        _accumulate_tool_call_deltas(tool_calls, delta.get("tool_calls"))
        message: dict[str, Any] = {
            "role": "assistant",
            "content": "".join(content_parts) or None,
        }
        if reasoning_parts:
            reasoning = "".join(reasoning_parts)
            message["reasoning"] = reasoning
            message["reasoning_details"] = [{"type": "reasoning.text", "text": reasoning}]
        if tool_calls:
            message["tool_calls"] = [_complete_tool_call(tool_calls[index]) for index in sorted(tool_calls)]
        return {
            "choices": [{"message": message, "finish_reason": finish_reason}],
            "usage": usage,
        }


class FakeOpenAIChatClient:
    def __init__(
        self,
        response_payload: dict[str, Any] | None = None,
        response_payloads: list[dict[str, Any]] | None = None,
        stream_chunks: list[str] | None = None,
    ) -> None:
        self.captured_payload: dict[str, Any] = {}
        self.captured_payloads: list[dict[str, Any]] = []
        self._response_payload = response_payload
        self._response_payloads = list(response_payloads or [])
        self._stream_chunks = list(stream_chunks or [])

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

    def stream_complete(
        self,
        payload: dict[str, Any],
        on_delta: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        self.captured_payload = payload
        self.captured_payloads.append(payload)
        for chunk in self._stream_chunks:
            if on_delta:
                on_delta(chunk)
        if self._response_payloads:
            return self._response_payloads.pop(0)
        if self._response_payload is not None:
            return self._response_payload
        content = "".join(self._stream_chunks) or "ok"
        return _assistant_response(content)


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


def _first_choice_message(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return {}
    choice = choices[0]
    if not isinstance(choice, dict):
        return {}
    message = choice.get("message")
    return message if isinstance(message, dict) else {}


def _stream_json_event(line: str) -> dict[str, Any] | None:
    if not line.startswith("data:"):
        return None
    data = line.removeprefix("data:").strip()
    if not data or data == "[DONE]":
        return None
    parsed = json.loads(data)
    return parsed if isinstance(parsed, dict) else None


def _delta_reasoning_text(delta: dict[str, Any]) -> str:
    parts: list[str] = []
    reasoning = delta.get("reasoning")
    if isinstance(reasoning, str):
        parts.append(reasoning)
    details = delta.get("reasoning_details")
    if isinstance(details, list):
        for detail in details:
            if not isinstance(detail, dict):
                continue
            text = detail.get("text") or detail.get("content")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)


def _accumulate_tool_call_deltas(tool_calls: dict[int, dict[str, Any]], deltas: Any) -> None:
    if not isinstance(deltas, list):
        return
    for delta in deltas:
        if not isinstance(delta, dict):
            continue
        index = int(delta.get("index") or 0)
        current = tool_calls.setdefault(index, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
        if delta.get("id"):
            current["id"] = str(delta["id"])
        if delta.get("type"):
            current["type"] = str(delta["type"])
        function_delta = delta.get("function")
        if isinstance(function_delta, dict):
            function = current.setdefault("function", {"name": "", "arguments": ""})
            if function_delta.get("name"):
                function["name"] = f"{function.get('name') or ''}{function_delta['name']}"
            if function_delta.get("arguments"):
                function["arguments"] = f"{function.get('arguments') or ''}{function_delta['arguments']}"


def _complete_tool_call(tool_call: dict[str, Any]) -> dict[str, Any]:
    if not tool_call.get("id"):
        raw_function = tool_call.get("function")
        function: dict[str, Any] = raw_function if isinstance(raw_function, dict) else {}
        tool_call["id"] = f"call_{function.get('name') or 'tool'}"
    return tool_call


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
        if isinstance(last_message, dict) and "LLM_JUDGE_EVALUATION" in str(last_message.get("content") or ""):
            return _mock_judge_response(str(last_message.get("content") or ""))
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


def _mock_judge_response(content: str) -> dict[str, Any]:
    expected = _extract_marker(content, "Expected output:", "Actual output:")
    actual = _extract_marker(content, "Actual output:", "Rubric:")
    passed = bool(expected) and expected.strip().lower() in actual.strip().lower()
    result = {
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "reason": "mock judge: expected answer is preserved" if passed else "mock judge: expected answer is missing",
    }
    return _assistant_response(json.dumps(result))


def _extract_marker(content: str, start: str, end: str) -> str:
    if start not in content:
        return ""
    after = content.split(start, 1)[1]
    if end in after:
        after = after.split(end, 1)[0]
    return after.strip()


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
