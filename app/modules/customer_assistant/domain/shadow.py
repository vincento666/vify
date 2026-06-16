from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from time import perf_counter
from typing import Any, Literal, Protocol

from app.core.config import Settings
from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)
from app.modules.customer_assistant.domain.models import TaskCommand
from app.modules.provider.api.facade import ProviderModelFacade
from app.modules.provider.infra.llm_adapters import OpenAIAdapterParser

ShadowMode = Literal["off", "fake", "live"]


class ShadowPhase(StrEnum):
    TASK_RECOGNITION = "task_recognition"
    RECOMMENDATION = "recommendation"


class CustomerAssistantShadowClient(Protocol):
    def recognize_tasks(self, *, message: str, commands: list[TaskCommand]) -> str:
        ...

    def recommend(
        self,
        *,
        task_summaries: list[dict[str, Any]],
        operator_recommendation: str,
        customer_reply_draft: str,
    ) -> str:
        ...


@dataclass(frozen=True)
class CustomerAssistantShadowSettings:
    mode: ShadowMode = "off"
    model_config_id: int | None = None
    task_recognition_enabled: bool = True
    recommendation_enabled: bool = True

    @classmethod
    def from_settings(cls, settings: Settings) -> CustomerAssistantShadowSettings:
        mode = str(settings.customer_assistant_llm_shadow_mode or "off").strip().lower()
        if mode not in {"off", "fake", "live"}:
            mode = "off"
        return cls(
            mode=mode,  # type: ignore[arg-type]
            model_config_id=settings.customer_assistant_llm_shadow_model_config_id,
            task_recognition_enabled=bool(settings.customer_assistant_llm_shadow_task_recognition),
            recommendation_enabled=bool(settings.customer_assistant_llm_shadow_recommendation),
        )


@dataclass(frozen=True)
class ShadowParseResult:
    ok: bool
    data: dict[str, Any]
    error: str | None = None


@dataclass(frozen=True)
class ShadowCallResult:
    ok: bool
    data: dict[str, Any]
    latency_ms: int
    error: str | None = None


class FakeCustomerAssistantShadowClient:
    def recognize_tasks(self, *, message: str, commands: list[TaskCommand]) -> str:
        return json.dumps(
            {
                "commands": [_command_shadow_payload(command) for command in commands],
                "confidence": 0.82 if commands else 0.0,
                "warnings": [] if commands else [f"No deterministic command for: {message[:40]}"],
            },
            ensure_ascii=False,
        )

    def recommend(
        self,
        *,
        task_summaries: list[dict[str, Any]],
        operator_recommendation: str,
        customer_reply_draft: str,
    ) -> str:
        return json.dumps(
            {
                "operatorRecommendation": operator_recommendation,
                "customerReplyDraft": customer_reply_draft,
                "warnings": [],
                "taskSummaries": [dict(summary) for summary in task_summaries],
            },
            ensure_ascii=False,
        )


class ProviderBackedCustomerAssistantShadowClient:
    def __init__(
        self,
        model_facade: ProviderModelFacade,
        model_config_id: int,
        request_builder: OpenAIChatRequestBuilder | None = None,
        parser: OpenAIAdapterParser | None = None,
        llm_client_factory: type[ProviderBackedOpenAIChatClient] = ProviderBackedOpenAIChatClient,
    ) -> None:
        self._model_facade = model_facade
        self._model_config_id = model_config_id
        self._request_builder = request_builder or OpenAIChatRequestBuilder()
        self._parser = parser or OpenAIAdapterParser()
        self._llm_client_factory = llm_client_factory

    def recognize_tasks(self, *, message: str, commands: list[TaskCommand]) -> str:
        prompt = (
            "Return strict JSON for customer-assistant task recognition shadow only. "
            "Schema: commands[], confidence, warnings[]. "
            f"Customer message: {message}\n"
            f"Deterministic baseline: {json.dumps([_command_shadow_payload(c) for c in commands], ensure_ascii=False)}"
        )
        return self._complete(prompt)

    def recommend(
        self,
        *,
        task_summaries: list[dict[str, Any]],
        operator_recommendation: str,
        customer_reply_draft: str,
    ) -> str:
        prompt = (
            "Return strict JSON for customer-assistant recommendation shadow only. "
            "Schema: operatorRecommendation, customerReplyDraft, warnings[], taskSummaries[]. "
            f"Task summaries: {json.dumps(task_summaries, ensure_ascii=False)}\n"
            f"Baseline operator recommendation: {operator_recommendation}\n"
            f"Baseline customer reply draft: {customer_reply_draft}"
        )
        return self._complete(prompt)

    def _complete(self, prompt: str) -> str:
        config = self._model_facade.get_enabled_model_config(self._model_config_id)
        payload = self._request_builder.build(
            model=config.model_id,
            messages=[
                ChatRequestMessage(role="system", content="Return JSON only. No markdown."),
                ChatRequestMessage(role="user", content=prompt),
            ],
            temperature=0,
            max_tokens=min(config.context_size, 2048),
            extra_params=config.extra_params,
        )
        client = self._llm_client_factory(
            ProviderChatConfig(
                provider_type=config.provider_type,
                base_url=config.provider_base_url,
                auth_config=config.provider_auth_config,
            )
        )
        return self._parser.parse_chat_response(client.complete(payload)).content


def parse_task_recognition_shadow_output(raw: str) -> ShadowParseResult:
    parsed = _parse_json_object(raw)
    if not parsed.ok:
        return parsed
    commands = parsed.data.get("commands")
    warnings = parsed.data.get("warnings")
    if not isinstance(commands, list):
        return ShadowParseResult(False, {}, "commands must be a list")
    if warnings is not None and not isinstance(warnings, list):
        return ShadowParseResult(False, {}, "warnings must be a list")
    normalized_commands: list[dict[str, Any]] = []
    for command in commands:
        if not isinstance(command, dict):
            return ShadowParseResult(False, {}, "command must be an object")
        missing = [
            key
            for key in ("type", "taskKey", "taskType", "businessKey", "workerType", "workerRef")
            if not command.get(key)
        ]
        if missing:
            return ShadowParseResult(False, {}, f"command missing {','.join(missing)}")
        normalized_commands.append({key: command.get(key) for key in _TASK_COMMAND_KEYS})
    return ShadowParseResult(
        True,
        {
            "commands": normalized_commands,
            "confidence": parsed.data.get("confidence"),
            "warnings": list(warnings or []),
        },
    )


def parse_recommendation_shadow_output(raw: str) -> ShadowParseResult:
    parsed = _parse_json_object(raw)
    if not parsed.ok:
        return parsed
    warnings = parsed.data.get("warnings")
    task_summaries = parsed.data.get("taskSummaries")
    if not isinstance(parsed.data.get("operatorRecommendation"), str):
        return ShadowParseResult(False, {}, "operatorRecommendation must be a string")
    if not isinstance(parsed.data.get("customerReplyDraft"), str):
        return ShadowParseResult(False, {}, "customerReplyDraft must be a string")
    if warnings is not None and not isinstance(warnings, list):
        return ShadowParseResult(False, {}, "warnings must be a list")
    if task_summaries is not None and not isinstance(task_summaries, list):
        return ShadowParseResult(False, {}, "taskSummaries must be a list")
    return ShadowParseResult(
        True,
        {
            "operatorRecommendation": parsed.data["operatorRecommendation"],
            "customerReplyDraft": parsed.data["customerReplyDraft"],
            "warnings": list(warnings or []),
            "taskSummaries": list(task_summaries or []),
        },
    )


def build_shadow_event_payload(
    *,
    phase: ShadowPhase,
    mode: ShadowMode,
    model_config_id: int | None,
    actor: str,
    baseline: dict[str, Any] | None = None,
    shadow: dict[str, Any] | None = None,
    diff: dict[str, Any] | None = None,
    latency_ms: int | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "phase": phase.value,
        "mode": mode,
        "modelConfigId": model_config_id,
        "actor": actor,
        "baseline": baseline,
        "shadow": shadow,
        "diff": diff,
        "latencyMs": latency_ms,
        "error": error,
    }


def call_shadow(
    call: Any,
    parser: Any,
) -> ShadowCallResult:
    started = perf_counter()
    try:
        raw = call()
        parsed = parser(raw)
    except Exception as exc:  # noqa: BLE001 - shadow must never fail main runtime.
        return ShadowCallResult(False, {}, _elapsed_ms(started), str(exc))
    if not parsed.ok:
        return ShadowCallResult(False, {}, _elapsed_ms(started), parsed.error)
    return ShadowCallResult(True, parsed.data, _elapsed_ms(started), None)


def _parse_json_object(raw: str) -> ShadowParseResult:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return ShadowParseResult(False, {}, f"invalid JSON: {exc.msg}")
    if not isinstance(parsed, dict):
        return ShadowParseResult(False, {}, "shadow output must be a JSON object")
    return ShadowParseResult(True, parsed)


def _elapsed_ms(started: float) -> int:
    return max(0, int((perf_counter() - started) * 1000))


_TASK_COMMAND_KEYS = ("type", "taskKey", "taskType", "businessKey", "workerType", "workerRef", "reason")


def _command_shadow_payload(command: TaskCommand) -> dict[str, Any]:
    return {
        "type": command.type.value,
        "taskKey": command.task_key,
        "taskType": command.task_type,
        "businessKey": command.business_key,
        "workerType": command.worker_type,
        "workerRef": command.worker_ref,
        "reason": command.reason,
    }
