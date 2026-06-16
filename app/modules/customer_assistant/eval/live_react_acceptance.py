from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)
from app.modules.chat.domain.tool_schema import ToolDefinition
from app.modules.customer_assistant.domain.llm_primary import (
    CustomerAssistantLlmRuntimeMode,
    CustomerAssistantLlmRuntimeSettings,
)
from app.modules.customer_assistant.domain.models import TaskCommand, TaskCommandType
from app.modules.customer_assistant.domain.react_core import CoreObservation
from app.modules.customer_assistant.domain.react_worker import (
    ReactModelAction,
    ReactWorkerModel,
    RestrictedReactWorker,
)
from app.modules.customer_assistant.domain.scheduler import LocalWorkerScheduler
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.domain.shadow import (
    CustomerAssistantShadowClient,
    parse_recommendation_shadow_output,
    parse_task_recognition_shadow_output,
)
from app.modules.customer_assistant.domain.two_stage import TWO_STAGE_FINAL_SCHEMA_VERSION, TwoStageFinalizer
from app.modules.customer_assistant.domain.worker_registry import ReactWorkerConfig
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)
from app.modules.provider.infra.llm_adapters import OpenAIAdapterParser
from app.modules.provider.infra.repository import ProviderRepository

LIVE_GATE_NAME = "customer-assistant-live-react-acceptance"
LIVE_GATE_FLAG = "HIFY_RUN_CUSTOMER_ASSISTANT_LIVE_REACT_ACCEPTANCE"
LIVE_MODEL_CONFIG_ID = "HIFY_CUSTOMER_ASSISTANT_LIVE_MODEL_CONFIG_ID"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL_POOL = ("xiaomi/mimo-v2-flash", "qwen/qwen3.5-9b", "deepseek/deepseek-v4-flash")
DEFAULT_OUTPUT_DIR = Path("artifacts/slices/072-customer-assistant-live-react-acceptance/live")
PROVIDER_TYPE = "OPENAI_COMPATIBLE"
REQUIRED_CATEGORIES = (
    "task_recognition_accuracy",
    "two_stage_recommendation_quality",
    "react_worker_tool_call_policy_and_event_echo",
)


@dataclass(frozen=True)
class LiveReactAcceptanceConfig:
    enabled: bool
    provider_type: str
    base_url: str
    api_key: str
    model_pool: tuple[str, ...]
    output_dir: Path = DEFAULT_OUTPUT_DIR


@dataclass(frozen=True)
class LiveCategoryResult:
    name: str
    status: Literal["passed", "failed", "skipped"]
    success_model: str = ""
    attempts: list[dict[str, str]] = field(default_factory=list)
    summary: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LiveAcceptanceResult:
    status: Literal["completed", "failed", "skipped"]
    live_model_calls: int = 0
    categories: list[LiveCategoryResult] = field(default_factory=list)
    evidence_path: str | None = None
    reason: str = ""
    warnings: list[str] = field(default_factory=list)


LiveRunner = Callable[[LiveReactAcceptanceConfig], LiveAcceptanceResult]


def load_live_react_acceptance_config(
    env: dict[str, str] | os._Environ[str] | None = None,
    output_dir: Path | None = None,
) -> LiveReactAcceptanceConfig:
    values = os.environ if env is None else env
    raw_model_pool = str(values.get("HIFY_CUSTOMER_ASSISTANT_LIVE_MODEL_POOL") or "")
    model_pool = _model_pool_from_env(raw_model_pool)
    base_url = str(
        values.get("HIFY_CUSTOMER_ASSISTANT_LIVE_BASE_URL")
        or values.get("OPENROUTER_BASE_URL")
        or DEFAULT_BASE_URL
    ).rstrip("/")
    api_key = str(values.get("HIFY_CUSTOMER_ASSISTANT_LIVE_API_KEY") or values.get("OPENROUTER_API_KEY") or "")
    provider_type = PROVIDER_TYPE
    if not api_key:
        provider_config = _provider_config_from_env(values)
        if provider_config is not None:
            provider_type = str(provider_config["provider_type"] or PROVIDER_TYPE)
            base_url = str(provider_config["provider_base_url"] or DEFAULT_BASE_URL).rstrip("/")
            auth_config = dict(provider_config.get("provider_auth_config") or {})
            api_key = str(auth_config.get("api_key") or auth_config.get("apiKey") or "")
            model_pool = (str(provider_config["model_id"]),)
    return LiveReactAcceptanceConfig(
        enabled=str(values.get(LIVE_GATE_FLAG) or "").strip() == "1",
        provider_type=provider_type,
        base_url=base_url,
        api_key=api_key,
        model_pool=model_pool,
        output_dir=output_dir or DEFAULT_OUTPUT_DIR,
    )


def run_customer_assistant_live_react_acceptance(
    *,
    env: dict[str, str] | os._Environ[str] | None = None,
    output_dir: Path | None = None,
    live_runner: LiveRunner | None = None,
) -> LiveAcceptanceResult:
    config = load_live_react_acceptance_config(env, output_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    if not config.enabled:
        result = LiveAcceptanceResult(
            status="skipped",
            reason=f"Set {LIVE_GATE_FLAG}=1 and an OpenRouter/OpenAI-compatible API key to run.",
        )
        artifact = config.output_dir / f"{LIVE_GATE_NAME}-skipped.md"
        _write_artifact(artifact, config, result)
        return replace(result, evidence_path=str(artifact))
    if not config.api_key:
        result = LiveAcceptanceResult(
            status="failed",
            reason=(
                "Missing HIFY_CUSTOMER_ASSISTANT_LIVE_API_KEY, OPENROUTER_API_KEY, "
                f"or resolvable {LIVE_MODEL_CONFIG_ID}."
            ),
        )
        artifact = config.output_dir / f"{LIVE_GATE_NAME}.md"
        _write_artifact(artifact, config, result)
        return replace(result, evidence_path=str(artifact))

    runner = live_runner or CustomerAssistantLiveReactAcceptanceRunner().run
    try:
        result = runner(config)
    except Exception as exc:  # noqa: BLE001 - live gate records provider/runtime failures as artifact evidence.
        result = LiveAcceptanceResult(status="failed", reason=str(exc)[:800])
    category_names = {category.name for category in result.categories}
    missing_categories = [name for name in REQUIRED_CATEGORIES if name not in category_names]
    if result.status == "completed" and missing_categories:
        result = replace(
            result,
            status="failed",
            reason=f"Missing required live acceptance categories: {', '.join(missing_categories)}.",
        )
    elif result.status == "completed" and any(category.status != "passed" for category in result.categories):
        result = replace(result, status="failed", reason="One or more live acceptance categories failed.")
    artifact = config.output_dir / f"{LIVE_GATE_NAME}.md"
    _write_artifact(artifact, config, result)
    return replace(result, evidence_path=str(artifact))


class CustomerAssistantLiveReactAcceptanceRunner:
    def run(self, config: LiveReactAcceptanceConfig) -> LiveAcceptanceResult:
        categories = [
            self._task_recognition_accuracy(config),
            self._two_stage_recommendation_quality(config),
            self._react_worker_tool_call_policy_and_event_echo(config),
        ]
        status: Literal["completed", "failed"] = (
            "completed" if all(category.status == "passed" for category in categories) else "failed"
        )
        return LiveAcceptanceResult(
            status=status,
            live_model_calls=sum(len(category.attempts) for category in categories),
            categories=categories,
            reason="" if status == "completed" else "One or more live categories failed.",
        )

    def _task_recognition_accuracy(self, config: LiveReactAcceptanceConfig) -> LiveCategoryResult:
        client = _LivePrimaryClient(config)
        try:
            with _customer_assistant_session("task-recognition") as session:
                service = CustomerAssistantService(
                    CustomerAssistantRepository(session),
                    llm_runtime_settings=CustomerAssistantLlmRuntimeSettings(
                        mode=CustomerAssistantLlmRuntimeMode.LLM_PRIMARY_WITH_FALLBACK,
                        min_confidence=0.70,
                    ),
                    llm_primary_client=client,
                )
                assistant_session = service.create_session({"liveGate": LIVE_GATE_NAME})
                session_id = int(assistant_session["id"])
                result = service.handle_turn(
                    session_id,
                    "帮我查随身包行李规则",
                    idempotency_key="live-task-recognition",
                )
                events = service.list_events(session_id)["list"]
            event_types = [str(event.get("type") or "") for event in events]
            selected = _event_payloads(events, "llm_primary_selected", phase="task_recognition")
            task_keys = [str(item.get("taskKey") or "") for item in result.get("taskSummaries", [])]
            _require(selected, "main runtime did not select the LLM primary task-recognition path")
            _require("baggage_qa" in task_keys, f"expected baggage_qa task, got {task_keys}")
            _require("task_recognized" in event_types, "task_recognized event was not persisted")
            return LiveCategoryResult(
                name="task_recognition_accuracy",
                status="passed",
                success_model=client.success_model("task_recognition"),
                attempts=client.attempts,
                summary="Main runtime selected baggage_qa through LLM primary path.",
                evidence={"taskKeys": task_keys, "eventTypes": event_types},
            )
        except Exception as exc:  # noqa: BLE001 - category result must preserve live failure evidence.
            return LiveCategoryResult(
                name="task_recognition_accuracy",
                status="failed",
                attempts=client.attempts,
                summary=str(exc)[:800],
            )

    def _two_stage_recommendation_quality(self, config: LiveReactAcceptanceConfig) -> LiveCategoryResult:
        finalizer = _LiveTwoStageFinalizer(config)
        try:
            with _customer_assistant_session("two-stage") as session:
                service = CustomerAssistantService(
                    CustomerAssistantRepository(session),
                    llm_runtime_settings=CustomerAssistantLlmRuntimeSettings(
                        mode=CustomerAssistantLlmRuntimeMode.TWO_STAGE_PRIMARY_WITH_FALLBACK
                    ),
                    two_stage_runtime=finalizer,
                )
                assistant_session = service.create_session({"liveGate": LIVE_GATE_NAME})
                session_id = int(assistant_session["id"])
                result = service.handle_turn(
                    session_id,
                    "请说明我的行李额度是多少",
                    idempotency_key="live-two-stage",
                )
                events = service.list_events(session_id)["list"]
            event_types = [str(event.get("type") or "") for event in events]
            _require("two_stage_plan_recorded" in event_types, "two-stage plan event was not persisted")
            _require("two_stage_action_recorded" in event_types, "two-stage action event was not persisted")
            _require("two_stage_observation_recorded" in event_types, "two-stage observation event was not persisted")
            _require("two_stage_primary_selected" in event_types, "two-stage primary recommendation was not selected")
            _require(result.get("customerReplyDraft"), "two-stage result did not produce a customer draft")
            return LiveCategoryResult(
                name="two_stage_recommendation_quality",
                status="passed",
                success_model=finalizer.success_model,
                attempts=finalizer.attempts,
                summary="Two-Stage runtime produced schema-valid, equivalence-gated final recommendation.",
                evidence={
                    "eventTypes": event_types,
                    "customerReplyDraftExcerpt": str(result.get("customerReplyDraft") or "")[:240],
                },
            )
        except Exception as exc:  # noqa: BLE001 - category result must preserve live failure evidence.
            return LiveCategoryResult(
                name="two_stage_recommendation_quality",
                status="failed",
                attempts=finalizer.attempts,
                summary=str(exc)[:800],
            )

    def _react_worker_tool_call_policy_and_event_echo(self, config: LiveReactAcceptanceConfig) -> LiveCategoryResult:
        read_model = _LiveReactToolModel(config, tool_name="lookup_order", risk="read")
        write_model = _LiveReactToolModel(config, tool_name="submit_refund", risk="write")
        write_tool_calls = 0
        try:
            with _customer_assistant_session("react-read") as session:
                service = CustomerAssistantService(
                    CustomerAssistantRepository(session),
                    core=cast(Any, _ReactTaskCore(message_business_key="TK-100")),
                    scheduler=LocalWorkerScheduler(
                        {
                            "react_worker": RestrictedReactWorker(
                                config=_react_worker_config(),
                                model=read_model,
                                tools={
                                    "lookup_order": lambda args: {
                                        "orderNo": args.get("orderNo") or "TK-100",
                                        "status": "refundable",
                                    }
                                },
                            )
                        }
                    ),
                )
                assistant_session = service.create_session({"liveGate": LIVE_GATE_NAME})
                read_session_id = int(assistant_session["id"])
                read_result = service.handle_turn(read_session_id, "查 TK-100", idempotency_key="live-react-read")
                read_events = service.list_events(read_session_id)["list"]

            def write_tool(args: dict[str, Any]) -> dict[str, Any]:
                nonlocal write_tool_calls
                write_tool_calls += 1
                return {"orderNo": args.get("orderNo"), "submitted": True}

            with _customer_assistant_session("react-write") as session:
                service = CustomerAssistantService(
                    CustomerAssistantRepository(session),
                    core=cast(Any, _ReactTaskCore(message_business_key="TK-100")),
                    scheduler=LocalWorkerScheduler(
                        {
                            "react_worker": RestrictedReactWorker(
                                config=_react_worker_config(allowed_tools=("lookup_order", "submit_refund")),
                                model=write_model,
                                tools={"submit_refund": write_tool},
                            )
                        }
                    ),
                )
                assistant_session = service.create_session({"liveGate": LIVE_GATE_NAME})
                write_session_id = int(assistant_session["id"])
                write_result = service.handle_turn(write_session_id, "提交 TK-100 退票", idempotency_key="live-react-write")
                write_events = service.list_events(write_session_id)["list"]

            read_event_types = [str(event.get("type") or "") for event in read_events]
            write_event_types = [str(event.get("type") or "") for event in write_events]
            _require(read_model.success_model, "read ReAct worker did not receive a live model tool call")
            _require(write_model.success_model, "write ReAct worker did not receive a live model tool call")
            for event_type in ("react_tool_call_started", "react_tool_call_completed", "react_observation_recorded"):
                _require(event_type in read_event_types, f"read ReAct event missing: {event_type}")
            _require("react_tool_call_started" in write_event_types, "write ReAct tool-start event missing")
            _require(write_tool_calls == 0, "high-risk write tool was executed instead of blocked")
            _require(write_result["taskSummaries"][0]["status"] == "WAITING", "high-risk write task did not remain WAITING")
            _require(write_result["proposedActions"], "high-risk write did not create a proposed action")
            return LiveCategoryResult(
                name="react_worker_tool_call_policy_and_event_echo",
                status="passed",
                success_model=read_model.success_model or write_model.success_model,
                attempts=[*read_model.attempts, *write_model.attempts],
                summary="ReAct worker observed live tool calls, event echo, and high-risk write blocking.",
                evidence={
                    "readEventTypes": read_event_types,
                    "writeEventTypes": write_event_types,
                    "readRecommendation": str(read_result.get("operatorRecommendation") or "")[:240],
                    "writeTaskStatus": write_result["taskSummaries"][0]["status"],
                    "writeToolExecutions": write_tool_calls,
                },
            )
        except Exception as exc:  # noqa: BLE001 - category result must preserve live failure evidence.
            return LiveCategoryResult(
                name="react_worker_tool_call_policy_and_event_echo",
                status="failed",
                attempts=[*read_model.attempts, *write_model.attempts],
                summary=str(exc)[:800],
                evidence={"writeToolExecutions": write_tool_calls},
            )


class _LivePrimaryClient(CustomerAssistantShadowClient):
    def __init__(self, config: LiveReactAcceptanceConfig) -> None:
        self._pool = _ModelPoolChat(config)
        self.attempts: list[dict[str, str]] = []
        self._success_by_phase: dict[str, str] = {}

    def recognize_tasks(self, *, message: str, commands: list[TaskCommand]) -> str:
        baseline = [_command_payload(command) for command in commands]
        prompt = (
            "Return strict JSON only for Hify customer-assistant task recognition. "
            "Select only from deterministic baseline commands. Do not invent commands. "
            "Schema: commands[], confidence, warnings[]. "
            f"Customer message: {message}\n"
            f"Deterministic baseline commands: {json.dumps(baseline, ensure_ascii=False)}"
        )

        def validate(content: str) -> str:
            parsed = parse_task_recognition_shadow_output(content)
            if not parsed.ok:
                raise ValueError(parsed.error or "invalid task-recognition JSON")
            task_keys = [str(item.get("taskKey") or "") for item in parsed.data["commands"]]
            if [item["taskKey"] for item in baseline] != task_keys:
                raise ValueError(f"model changed task keys from baseline: {task_keys}")
            if float(parsed.data.get("confidence") or 0.0) < 0.70:
                raise ValueError("confidence below primary threshold")
            return content

        content, attempts, success_model = self._pool.complete_json(
            phase="task_recognition",
            prompt=prompt,
            max_tokens=900,
            validate=validate,
        )
        self.attempts.extend(attempts)
        self._success_by_phase["task_recognition"] = success_model
        return content

    def recommend(
        self,
        *,
        task_summaries: list[dict[str, Any]],
        operator_recommendation: str,
        customer_reply_draft: str,
    ) -> str:
        prompt = (
            "Return strict JSON only for Hify customer-assistant recommendation. "
            "Preserve the baseline operatorRecommendation and customerReplyDraft exactly. "
            "Schema: operatorRecommendation, customerReplyDraft, warnings[], taskSummaries[]. "
            f"Task summaries: {json.dumps(task_summaries, ensure_ascii=False)}\n"
            f"Baseline operatorRecommendation: {operator_recommendation}\n"
            f"Baseline customerReplyDraft: {customer_reply_draft}"
        )

        def validate(content: str) -> str:
            parsed = parse_recommendation_shadow_output(content)
            if not parsed.ok:
                raise ValueError(parsed.error or "invalid recommendation JSON")
            if parsed.data["operatorRecommendation"] != operator_recommendation:
                raise ValueError("operatorRecommendation differs from baseline")
            if parsed.data["customerReplyDraft"] != customer_reply_draft:
                raise ValueError("customerReplyDraft differs from baseline")
            return content

        content, attempts, success_model = self._pool.complete_json(
            phase="recommendation",
            prompt=prompt,
            max_tokens=1200,
            validate=validate,
        )
        self.attempts.extend(attempts)
        self._success_by_phase["recommendation"] = success_model
        return content

    def success_model(self, phase: str) -> str:
        return self._success_by_phase.get(phase, "")


class _LiveTwoStageFinalizer(TwoStageFinalizer):
    def __init__(self, config: LiveReactAcceptanceConfig) -> None:
        self._pool = _ModelPoolChat(config)
        self.attempts: list[dict[str, str]] = []
        self.success_model = ""

    def finalize(self, input_pack: dict[str, Any], baseline_result: Any) -> dict[str, Any]:
        baseline = {
            "operatorRecommendation": baseline_result.operator_recommendation,
            "customerReplyDraft": baseline_result.customer_reply_draft,
            "warnings": list(baseline_result.warnings),
        }
        prompt = (
            "Return strict JSON only for Hify customer-assistant Two-Stage ReAct finalization. "
            "You must preserve the baseline final recommendation exactly so the promotion gate can compare it. "
            f"Required schemaVersion: {TWO_STAGE_FINAL_SCHEMA_VERSION}\n"
            f"Input pack: {json.dumps(input_pack, ensure_ascii=False)}\n"
            f"Baseline final: {json.dumps(baseline, ensure_ascii=False)}"
        )

        def validate(content: str) -> str:
            parsed = _json_object(content)
            if parsed.get("schemaVersion") != TWO_STAGE_FINAL_SCHEMA_VERSION:
                raise ValueError("schemaVersion mismatch")
            if parsed.get("operatorRecommendation") != baseline["operatorRecommendation"]:
                raise ValueError("operatorRecommendation differs from baseline")
            if parsed.get("customerReplyDraft") != baseline["customerReplyDraft"]:
                raise ValueError("customerReplyDraft differs from baseline")
            warnings = parsed.get("warnings")
            if warnings is not None and not isinstance(warnings, list):
                raise ValueError("warnings must be a list")
            return content

        content, attempts, success_model = self._pool.complete_json(
            phase="two_stage_final",
            prompt=prompt,
            max_tokens=1400,
            validate=validate,
        )
        self.attempts.extend(attempts)
        self.success_model = success_model
        return _json_object(content)


class _LiveReactToolModel(ReactWorkerModel):
    def __init__(self, config: LiveReactAcceptanceConfig, *, tool_name: str, risk: Literal["read", "write"]) -> None:
        self._pool = _ModelPoolChat(config)
        self._tool_name = tool_name
        self._risk = risk
        self.attempts: list[dict[str, str]] = []
        self.success_model = ""

    def next_action(
        self,
        *,
        task: Any,
        message: str,
        observation: dict[str, Any] | None,
        iteration: int,
    ) -> ReactModelAction:
        del iteration
        if observation is not None:
            status = str(observation.get("status") or "unknown")
            return ReactModelAction.final(
                operator_recommendation=f"Live ReAct lookup for {task.business_key}: {status}",
                customer_reply_draft=f"订单 {task.business_key} 当前状态：{status}。",
            )

        tool = _react_tool_definition(self._tool_name)
        prompt = (
            f"Use the provided tool `{self._tool_name}` for the customer-assistant ReAct worker. "
            f"Task business key: {task.business_key}. Customer message: {message}. "
            "Do not answer directly."
        )
        tool_call, attempts, success_model = self._pool.complete_tool_call(
            phase=f"react_{self._tool_name}",
            prompt=prompt,
            tool=tool,
        )
        self.attempts.extend(attempts)
        self.success_model = success_model
        args = dict(tool_call.arguments)
        args.setdefault("orderNo", task.business_key)
        return ReactModelAction.request_tool(self._tool_name, args, risk=self._risk)


class _ModelPoolChat:
    def __init__(self, config: LiveReactAcceptanceConfig) -> None:
        self._config = config
        self._builder = OpenAIChatRequestBuilder()
        self._parser = OpenAIAdapterParser()
        self._client = ProviderBackedOpenAIChatClient(
            ProviderChatConfig(
                provider_type=config.provider_type,
                base_url=config.base_url,
                auth_config={"api_key": config.api_key},
            ),
            timeout=60,
            max_attempts=1,
            retry_sleep=0,
        )

    def complete_json(
        self,
        *,
        phase: str,
        prompt: str,
        max_tokens: int,
        validate: Callable[[str], str],
    ) -> tuple[str, list[dict[str, str]], str]:
        attempts: list[dict[str, str]] = []
        for model in self._config.model_pool:
            try:
                payload = self._builder.build(
                    model=model,
                    messages=[
                        ChatRequestMessage(role="system", content="Return JSON only. No markdown."),
                        ChatRequestMessage(role="user", content=prompt),
                    ],
                    temperature=0,
                    max_tokens=max_tokens,
                    extra_params={
                        "response_format": {"type": "json_object"},
                        "reasoning": {"effort": "none", "exclude": True},
                    },
                )
                content = self._parser.parse_chat_response(self._client.complete(payload)).content
                validated = validate(content)
                attempts.append({"phase": phase, "model": model, "status": "passed", "error": ""})
                return validated, attempts, model
            except Exception as exc:  # noqa: BLE001 - model fallback must record live provider/schema failures.
                attempts.append({"phase": phase, "model": model, "status": "failed", "error": str(exc)[:300]})
        raise RuntimeError(f"No model passed phase {phase}: {attempts}")

    def complete_tool_call(
        self,
        *,
        phase: str,
        prompt: str,
        tool: ToolDefinition,
    ) -> tuple[Any, list[dict[str, str]], str]:
        attempts: list[dict[str, str]] = []
        for model in self._config.model_pool:
            try:
                payload = self._builder.build(
                    model=model,
                    messages=[
                        ChatRequestMessage(
                            role="system",
                            content="You are a ReAct worker. Use the provided tool call. Do not answer directly.",
                        ),
                        ChatRequestMessage(role="user", content=prompt),
                    ],
                    tools=[tool],
                    temperature=0,
                    max_tokens=300,
                    extra_params={
                        "tool_choice": {"type": "function", "function": {"name": tool.name}},
                        "reasoning": {"effort": "none", "exclude": True},
                    },
                )
                parsed = self._parser.parse_chat_response(self._client.complete(payload))
                if not parsed.tool_calls:
                    raise ValueError("model did not return tool_calls")
                selected = parsed.tool_calls[0]
                if selected.name != tool.name:
                    raise ValueError(f"model selected unexpected tool: {selected.name}")
                attempts.append({"phase": phase, "model": model, "status": "passed", "error": ""})
                return selected, attempts, model
            except Exception as exc:  # noqa: BLE001 - model fallback must record live provider/schema failures.
                attempts.append({"phase": phase, "model": model, "status": "failed", "error": str(exc)[:300]})
        raise RuntimeError(f"No model returned required tool call for phase {phase}: {attempts}")


class _ReactTaskCore:
    def __init__(self, *, message_business_key: str) -> None:
        self._business_key = message_business_key

    def run(
        self,
        context: Any,
        action_handler: Callable[[list[TaskCommand]], dict[str, Any]],
        finalizer: Callable[[CoreObservation], Any],
    ) -> Any:
        command = TaskCommand(
            TaskCommandType.ADD_TASK,
            task_key=f"refund_status:{self._business_key}",
            task_type="refund_status",
            business_key=self._business_key,
            worker_type="react_worker",
            worker_ref="refund_status_react",
            reason="live_acceptance_react_task",
        )
        action_result = action_handler([command])
        return finalizer(CoreObservation(commands=(command,), action_result=action_result))


@contextmanager
def _customer_assistant_session(name: str) -> Iterator[Session]:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / f"{name}.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    register_customer_assistant_tables()
    Base.metadata.create_all(bind=engine, tables=customer_assistant_tables())
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        tmp_dir.cleanup()


def _model_pool_from_env(value: str) -> tuple[str, ...]:
    if not value.strip():
        return DEFAULT_MODEL_POOL
    models = tuple(item.strip() for item in value.split(",") if item.strip())
    return models or DEFAULT_MODEL_POOL


def _provider_config_from_env(env: dict[str, str] | os._Environ[str]) -> dict[str, Any] | None:
    raw_model_config_id = str(env.get(LIVE_MODEL_CONFIG_ID) or "").strip()
    if not raw_model_config_id:
        return None
    try:
        model_config_id = int(raw_model_config_id)
    except ValueError:
        return None
    if model_config_id <= 0:
        return None
    database_url = str(env.get("HIFY_DATABASE_URL") or "").strip()
    if not database_url:
        return None
    try:
        engine = create_engine(database_url, future=True)
        factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
        with factory() as session:
            row = ProviderRepository(session).get_enabled_model_config(model_config_id)
            return row if _is_supported_provider_config(row) else None
    except Exception:  # noqa: BLE001 - live gate fails closed without leaking DB/provider details.
        return None
    finally:
        if "engine" in locals():
            engine.dispose()


def _is_supported_provider_config(row: dict[str, Any] | None) -> bool:
    if row is None:
        return False
    if str(row.get("provider_type") or "") != PROVIDER_TYPE:
        return False
    parsed = urlparse(str(row.get("provider_base_url") or ""))
    if parsed.scheme not in {"http", "https"}:
        return False
    return not parsed.username and not parsed.password


def _write_artifact(path: Path, config: LiveReactAcceptanceConfig, result: LiveAcceptanceResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {LIVE_GATE_NAME}",
        "",
        f"- Status: `{result.status}`",
        f"- Provider type: `{config.provider_type}`",
        f"- Base URL: `{config.base_url}`",
        f"- Model pool: `{', '.join(config.model_pool)}`",
        "- API key: runtime environment only, not recorded",
        f"- Live model calls: `{result.live_model_calls}`",
    ]
    if result.reason:
        lines.append(f"- Reason: {_redacted_inline(result.reason, config)}")
    if result.warnings:
        lines.append(f"- Warnings: `{json.dumps(_redact(result.warnings, config), ensure_ascii=False)}`")
    lines.extend(["", "## Categories", ""])
    if not result.categories:
        lines.append("- No categories executed.")
    for category in result.categories:
        lines.extend(
            [
                f"### {category.name}",
                "",
                f"- Status: `{category.status}`",
                f"- Success model: `{category.success_model or 'n/a'}`",
                f"- Summary: {_redacted_inline(category.summary, config)}",
                "- Attempts:",
            ]
        )
        if not category.attempts:
            lines.append("  - none")
        for attempt in category.attempts:
            safe_attempt = _redact(attempt, config)
            lines.append(
                "  - "
                f"`{safe_attempt.get('phase', 'n/a')}` "
                f"`{safe_attempt.get('model', 'n/a')}` "
                f"{safe_attempt.get('status', 'unknown')} "
                f"{safe_attempt.get('error', '')}".rstrip()
            )
        if category.evidence:
            lines.extend(
                [
                    "- Evidence:",
                    f"```json\n{json.dumps(_redact(category.evidence, config), ensure_ascii=False, indent=2)}\n```",
                ]
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _command_payload(command: TaskCommand) -> dict[str, Any]:
    return {
        "type": command.type.value,
        "taskKey": command.task_key,
        "taskType": command.task_type,
        "businessKey": command.business_key,
        "workerType": command.worker_type,
        "workerRef": command.worker_ref,
        "reason": command.reason,
    }


def _event_payloads(events: list[dict[str, Any]], event_type: str, *, phase: str | None = None) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for event in events:
        if event.get("type") != event_type:
            continue
        payload = dict(event.get("payload") or {})
        if phase is None or payload.get("phase") == phase:
            payloads.append(payload)
    return payloads


def _react_worker_config(allowed_tools: tuple[str, ...] = ("lookup_order", "submit_refund")) -> ReactWorkerConfig:
    return ReactWorkerConfig(
        worker_ref="refund_status_react",
        task_type="refund_status",
        allowed_tools=allowed_tools,
        max_iterations=3,
        timeout_ms=15_000,
    )


def _react_tool_definition(name: str) -> ToolDefinition:
    descriptions = {
        "lookup_order": "Lookup an order by order number.",
        "submit_refund": "Submit a refund request by order number.",
    }
    return ToolDefinition(
        name=name,
        description=descriptions.get(name, name),
        parameters={
            "type": "object",
            "properties": {
                "orderNo": {
                    "type": "string",
                    "description": "Order number such as TK-100.",
                }
            },
            "required": ["orderNo"],
            "additionalProperties": False,
        },
    )


def _json_object(content: str) -> dict[str, Any]:
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("model response must be a JSON object")
    return parsed


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _redact(value: Any, config: LiveReactAcceptanceConfig) -> Any:
    secret_values = {item for item in (config.api_key,) if item}
    secret_keys = {"api_key", "apikey", "authorization", "password", "secret", "token", "credential", "credentials"}
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in secret_keys:
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = _redact(item, config)
        return redacted
    if isinstance(value, list):
        return [_redact(item, config) for item in value]
    if isinstance(value, str):
        redacted_text = value
        for secret in secret_values:
            redacted_text = redacted_text.replace(secret, "[REDACTED]")
        return redacted_text
    return value


def _redacted_inline(value: str, config: LiveReactAcceptanceConfig) -> str:
    return str(_redact(value, config)).replace("\n", " ")[:1000]
