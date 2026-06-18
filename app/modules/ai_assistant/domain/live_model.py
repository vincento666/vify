from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Callable, Protocol

from app.core.config import Settings
from app.modules.ai_assistant.domain.tools import ToolRegistry
from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)
from app.modules.chat.domain.tool_schema import ToolDefinition


@dataclass(frozen=True)
class LivePlannerConfig:
    base_url: str
    model: str
    api_key_ref: str = "env:OPENROUTER_API_KEY"
    api_key: str = ""
    provider: str = "openrouter"
    temperature: float = 0
    max_tokens: int = 1024


@dataclass(frozen=True)
class LivePlannerDecision:
    final_answer: str
    thought_summary: str
    stream_chunks: list[str]
    tool_calls: list[dict[str, Any]]
    usage: dict[str, int]
    model: str
    provider: str = "openrouter"
    streaming: bool = False
    stream_source: str = "post_completion_split"


class ChatCompletionClient(Protocol):
    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...


class StreamingChatCompletionClient(ChatCompletionClient, Protocol):
    def stream_complete(
        self,
        payload: dict[str, Any],
        on_delta: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        ...


class QwenLivePlanner:
    def __init__(
        self,
        config: LivePlannerConfig,
        *,
        client: ChatCompletionClient | None = None,
        builder: OpenAIChatRequestBuilder | None = None,
    ) -> None:
        self._config = config
        self._builder = builder or OpenAIChatRequestBuilder()
        self._client = client or ProviderBackedOpenAIChatClient(
            ProviderChatConfig(
                provider_type=config.provider,
                base_url=config.base_url,
                auth_config=_auth_config(config),
            )
        )

    @property
    def model(self) -> str:
        return self._config.model

    def with_config(self, config: LivePlannerConfig) -> QwenLivePlanner:
        reusable_client = None if isinstance(self._client, ProviderBackedOpenAIChatClient) else self._client
        return QwenLivePlanner(config, client=reusable_client, builder=self._builder)

    def plan(
        self,
        user_message: str,
        tool_registry: ToolRegistry,
        on_stream_chunk: Callable[[str, int], None] | None = None,
    ) -> LivePlannerDecision:
        return self.plan_messages(
            self.initial_messages(user_message),
            tool_registry,
            on_stream_chunk=on_stream_chunk,
        )

    def initial_messages(self, user_message: str) -> list[ChatRequestMessage]:
        return [
            ChatRequestMessage(
                role="system",
                content=(
                    "你是 Hify AI 助手。请用中文给出简短思考摘要，"
                    "不要输出隐藏推理。用户要求工具调用、文件读写、"
                    "skill 调用、知识库检索或执行回显时，必须使用提供的 function tools，"
                    "不要只用文字描述计划。工具执行后会收到 tool 结果，"
                    "如果原任务仍需要后续工具，请继续返回 function tool_calls。"
                ),
            ),
            ChatRequestMessage(role="user", content=user_message),
        ]

    def plan_messages(
        self,
        messages: list[ChatRequestMessage],
        tool_registry: ToolRegistry,
        on_stream_chunk: Callable[[str, int], None] | None = None,
    ) -> LivePlannerDecision:
        payload = self._builder.build(
            model=self._config.model,
            messages=messages,
            tools=[
                ToolDefinition(
                    name=manifest.name,
                    description=manifest.description,
                    parameters=manifest.input_schema,
                )
                for manifest in tool_registry.list_manifests()
            ],
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
        )
        streamed_chunks: list[str] = []
        if hasattr(self._client, "stream_complete"):
            response = self._stream_complete(payload, streamed_chunks, on_stream_chunk)
            streaming = bool(streamed_chunks)
            stream_source = "openrouter_delta" if streaming else "post_completion_split"
        else:
            response = self._client.complete(payload)
            streaming = False
            stream_source = "post_completion_split"
        message = _first_message(response)
        content = _message_content(message)
        reasoning = _message_reasoning(message)
        tool_calls = _tool_calls(message)
        summary = _thought_summary(content=content, reasoning=reasoning, has_tool_calls=bool(tool_calls))
        return LivePlannerDecision(
            final_answer=content,
            thought_summary=summary,
            stream_chunks=streamed_chunks if streamed_chunks else (_stream_chunks(content) if content else []),
            tool_calls=tool_calls,
            usage=_usage(response),
            model=self._config.model,
            provider=self._config.provider,
            streaming=streaming,
            stream_source=stream_source,
        )

    def _stream_complete(
        self,
        payload: dict[str, Any],
        streamed_chunks: list[str],
        on_stream_chunk: Callable[[str, int], None] | None,
    ) -> dict[str, Any]:
        client = self._client
        if not hasattr(client, "stream_complete"):
            raise RuntimeError("stream_complete is unavailable")

        def forward(chunk: str) -> None:
            if not chunk:
                return
            streamed_chunks.append(chunk)
            if on_stream_chunk:
                on_stream_chunk(chunk, len(streamed_chunks))

        return client.stream_complete(payload, on_delta=forward)  # type: ignore[attr-defined]


def create_qwen_live_planner(settings: Settings) -> QwenLivePlanner | None:
    api_key = settings.ai_assistant_openrouter_api_key.strip()
    key_ref = f"env:{settings.ai_assistant_openrouter_api_key_env.strip() or 'OPENROUTER_API_KEY'}"
    env_key = os.getenv(key_ref.removeprefix("env:"), "")
    if not api_key and not env_key:
        return None
    return QwenLivePlanner(
        LivePlannerConfig(
            base_url=settings.ai_assistant_openrouter_base_url,
            model=settings.ai_assistant_openrouter_model,
            api_key=api_key,
            api_key_ref=key_ref,
            provider="openrouter",
        )
    )


def _auth_config(config: LivePlannerConfig) -> dict[str, Any]:
    if config.api_key:
        return {"api_key": config.api_key}
    return {"api_key_ref": config.api_key_ref}


def _first_message(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return {}
    first = choices[0]
    if not isinstance(first, dict):
        return {}
    message = first.get("message")
    return message if isinstance(message, dict) else {}


def _message_content(message: dict[str, Any]) -> str:
    return _message_text(message.get("content"))


def _message_reasoning(message: dict[str, Any]) -> str:
    parts: list[str] = []
    _append_unique_text(parts, _message_text(message.get("reasoning")))
    details = message.get("reasoning_details")
    if isinstance(details, list):
        for detail in details:
            if isinstance(detail, dict):
                _append_unique_text(parts, _message_text(detail.get("text")))
                _append_unique_text(parts, _message_text(detail.get("content")))
            else:
                _append_unique_text(parts, _message_text(detail))
    return "\n".join(parts).strip()


def _message_text(raw: Any) -> str:
    if isinstance(raw, str):
        return _normalize_repeated_text(raw)
    if isinstance(raw, list):
        parts: list[str] = []
        for item in raw:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return _normalize_repeated_text("".join(parts))
    return ""


def _append_unique_text(parts: list[str], text: str) -> None:
    if not text:
        return
    existing = "\n".join(parts)
    if text in existing:
        return
    parts.append(text)


def _thought_summary(*, content: str, reasoning: str, has_tool_calls: bool) -> str:
    if reasoning:
        return _normalize_repeated_text(reasoning)
    if content:
        return "模型已返回可展示输出。"
    if has_tool_calls:
        return "已根据请求规划工具调用。"
    return "模型未返回可展示正文。"


def _tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    calls = message.get("tool_calls")
    if not isinstance(calls, list):
        return []
    planned: list[dict[str, Any]] = []
    for call in calls:
        if not isinstance(call, dict):
            continue
        function = call.get("function")
        if not isinstance(function, dict):
            continue
        name = str(function.get("name") or "")
        if not name:
            continue
        planned.append(
            {
                "toolName": name,
                "toolInput": _arguments(function.get("arguments")),
                "toolCallId": str(call.get("id") or f"call_{name}"),
            }
        )
    return planned


def _arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    return parsed if isinstance(parsed, dict) else {}


def _stream_chunks(content: str) -> list[str]:
    text = content.strip()
    if not text:
        return ["已收到模型规划结果。"]
    if len(text) <= 48:
        return [text]
    return [text[index : index + 48] for index in range(0, len(text), 48)]


def _normalize_repeated_text(value: str) -> str:
    text = value.strip()
    for _ in range(4):
        collapsed = _collapse_adjacent_repeated_units(text)
        if collapsed == text:
            break
        text = collapsed
    return text


def _collapse_adjacent_repeated_units(text: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(text):
        max_unit_length = min(32, (len(text) - index) // 2)
        matched = False
        for unit_length in range(max_unit_length, 1, -1):
            unit = text[index : index + unit_length]
            if not _has_text_signal(unit):
                continue
            next_unit = text[index + unit_length : index + unit_length * 2]
            if unit == next_unit:
                output.append(unit)
                index += unit_length * 2
                matched = True
                break
        if not matched:
            output.append(text[index])
            index += 1
    return "".join(output)


def _has_text_signal(value: str) -> bool:
    return bool(any(char.isalnum() or char == "_" or "\u4e00" <= char <= "\u9fff" for char in value))


def _usage(response: dict[str, Any]) -> dict[str, int]:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}
    input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
    return {
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": total_tokens,
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "total_tokens": total_tokens,
    }
