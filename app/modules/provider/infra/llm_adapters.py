from dataclasses import dataclass
import json
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ChatCompletionResult:
    content: str
    finish_reason: str | None
    tokens: int | None
    tool_calls: list[ToolCall]
    usage: dict[str, Any]


class OpenAIAdapterParser:
    def parse_chat_response(self, payload: dict[str, Any]) -> ChatCompletionResult:
        choice = payload.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = payload.get("usage", {})
        return ChatCompletionResult(
            content=str(message.get("content") or ""),
            finish_reason=choice.get("finish_reason"),
            tokens=usage.get("total_tokens"),
            tool_calls=self._parse_tool_calls(message.get("tool_calls", [])),
            usage=dict(usage) if isinstance(usage, dict) else {},
        )

    def _parse_tool_calls(self, raw_calls: Any) -> list[ToolCall]:
        if not isinstance(raw_calls, list):
            return []
        parsed: list[ToolCall] = []
        for raw_call in raw_calls:
            if not isinstance(raw_call, dict):
                continue
            function = raw_call.get("function", {})
            if not isinstance(function, dict):
                continue
            parsed.append(
                ToolCall(
                    id=str(raw_call.get("id") or ""),
                    name=str(function.get("name") or ""),
                    arguments=_parse_arguments(function.get("arguments")),
                )
            )
        return parsed

    def parse_stream_lines(self, lines: list[str]) -> list[str]:
        deltas: list[str] = []
        for line in lines:
            if not line.startswith("data: "):
                continue
            data = line.removeprefix("data: ").strip()
            if data == "[DONE]":
                continue
            payload = json.loads(data)
            choice = payload.get("choices", [{}])[0]
            content = choice.get("delta", {}).get("content")
            if content:
                deltas.append(str(content))
        return deltas


class AnthropicAdapterParser:
    def parse_chat_response(self, payload: dict[str, Any]) -> ChatCompletionResult:
        parts = payload.get("content", [])
        text = "".join(str(part.get("text", "")) for part in parts if part.get("type") == "text")
        return ChatCompletionResult(
            content=text,
            finish_reason=payload.get("stop_reason"),
            tokens=payload.get("usage", {}).get("output_tokens"),
            tool_calls=[],
            usage=dict(payload.get("usage") or {}) if isinstance(payload.get("usage"), dict) else {},
        )


class OllamaAdapterParser:
    def parse_chat_response(self, payload: dict[str, Any]) -> ChatCompletionResult:
        message = payload.get("message", {})
        return ChatCompletionResult(
            content=str(message.get("content") or ""),
            finish_reason=payload.get("done_reason"),
            tokens=None,
            tool_calls=[],
            usage={},
        )


def _parse_arguments(raw_arguments: Any) -> dict[str, Any]:
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if not isinstance(raw_arguments, str) or not raw_arguments.strip():
        return {}
    try:
        parsed = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
