from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Literal, Protocol

from app.modules.agent_harness import (
    AgentHarness,
    HarnessDecision,
    HarnessObservation,
    HarnessRunRequest,
    HarnessRunResult,
    HarnessRunStatus,
    HarnessToolAuthorization,
    HarnessToolCall,
    HarnessToolFailure,
)
from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus, WorkerResult
from app.modules.customer_assistant.domain.tool_policy import (
    ReactToolPolicy,
    UnsupportedReactToolPolicyError,
    react_tool_policy_for_ref,
)
from app.modules.customer_assistant.domain.worker_registry import ReactWorkerConfig

ReactTool = Callable[[dict[str, Any]], dict[str, Any]]
EVENT_SCHEMA_VERSION = "customer_assistant.react_worker.event/1"
OBSERVATION_SCHEMA_VERSION = "customer_assistant.react_observation/1"
FINAL_SCHEMA_VERSION = "customer_assistant.react_final/1"
_SECRET_KEYS = {"api_key", "apikey", "authorization", "password", "secret", "token", "credential", "credentials"}


@dataclass(frozen=True)
class ReactToolCall:
    name: str
    arguments: dict[str, Any]
    risk: Literal["read", "write"] = "read"


@dataclass(frozen=True)
class ReactModelAction:
    kind: Literal["tool_call", "final"]
    tool_call: ReactToolCall | None = None
    operator_recommendation: str = ""
    customer_reply_draft: str = ""

    @classmethod
    def request_tool(
        cls,
        name: str,
        arguments: dict[str, Any],
        *,
        risk: Literal["read", "write"] = "read",
    ) -> ReactModelAction:
        return cls(kind="tool_call", tool_call=ReactToolCall(name=name, arguments=arguments, risk=risk))

    @classmethod
    def final(cls, *, operator_recommendation: str, customer_reply_draft: str) -> ReactModelAction:
        return cls(
            kind="final",
            operator_recommendation=operator_recommendation,
            customer_reply_draft=customer_reply_draft,
        )


class ReactWorkerModel(Protocol):
    def next_action(
        self,
        *,
        task: TaskItem,
        message: str,
        observation: dict[str, Any] | None,
        iteration: int,
    ) -> ReactModelAction:
        ...


class FakeReactWorkerModel:
    def __init__(self, actions: list[ReactModelAction]) -> None:
        self._actions = list(actions)

    def next_action(
        self,
        *,
        task: TaskItem,
        message: str,
        observation: dict[str, Any] | None,
        iteration: int,
    ) -> ReactModelAction:
        del task, message, observation, iteration
        if self._actions:
            return self._actions.pop(0)
        return ReactModelAction.final(operator_recommendation="No further action.", customer_reply_draft="")


class DeterministicReactWorkerModel:
    def next_action(
        self,
        *,
        task: TaskItem,
        message: str,
        observation: dict[str, Any] | None,
        iteration: int,
    ) -> ReactModelAction:
        del message, iteration
        if observation is None:
            return ReactModelAction.request_tool("lookup_order", {"orderNo": task.business_key})
        status = str(observation.get("status") or "unknown")
        return ReactModelAction.final(
            operator_recommendation=f"{task.business_key} lookup status: {status}",
            customer_reply_draft=f"订单 {task.business_key} 当前状态：{status}。",
        )


class RestrictedReactWorker:
    def __init__(
        self,
        *,
        config: ReactWorkerConfig,
        model: ReactWorkerModel,
        tools: dict[str, ReactTool],
        policy: ReactToolPolicy | None = None,
        harness: AgentHarness | None = None,
    ) -> None:
        self._config = config
        self._model = model
        self._tools = dict(tools)
        self._policy = policy or react_tool_policy_for_ref(
            policy_ref=config.tool_policy_ref,
            allowed_tools=config.allowed_tools,
        )
        self._harness = harness or AgentHarness()

    def run(self, task: TaskItem, message: str) -> WorkerResult:
        profile = _CustomerAssistantHarnessProfile(
            task=task,
            message=message,
            model=self._model,
            tools=self._tools,
            policy=self._policy,
        )
        result = self._harness.execute(
            HarnessRunRequest(
                run_id=task.task_key,
                input={"message": message},
                max_iterations=self._config.max_iterations,
                timeout_ms=self._config.timeout_ms,
            ),
            profile,
        )
        return _customer_worker_result(
            task=task,
            config=self._config,
            result=result,
        )


class _CustomerAssistantHarnessProfile:
    def __init__(
        self,
        *,
        task: TaskItem,
        message: str,
        model: ReactWorkerModel,
        tools: dict[str, ReactTool],
        policy: ReactToolPolicy,
    ) -> None:
        self._task = task
        self._message = message
        self._model = model
        self._tools = tools
        self._policy = policy

    def plan(
        self,
        request: HarnessRunRequest,
        observations: tuple[HarnessObservation, ...],
        iteration: int,
    ) -> HarnessDecision:
        del request
        action = self._model.next_action(
            task=self._task,
            message=self._message,
            observation=observations[-1].output if observations else None,
            iteration=iteration,
        )
        if action.kind == "final":
            return HarnessDecision.finish(
                {
                    "operatorRecommendation": action.operator_recommendation,
                    "customerReplyDraft": action.customer_reply_draft,
                }
            )
        if action.tool_call is None:
            return HarnessDecision()
        return HarnessDecision.request_tools(
            HarnessToolCall(
                call_id=f"{iteration}:{action.tool_call.name}",
                name=action.tool_call.name,
                arguments=dict(action.tool_call.arguments),
                risk=action.tool_call.risk,
            )
        )

    def authorize_tool(
        self,
        request: HarnessRunRequest,
        call: HarnessToolCall,
    ) -> HarnessToolAuthorization:
        del request
        if not self._policy.is_allowed(call.name):
            return HarnessToolAuthorization.deny(f"Tool not allowed: {call.name}")
        if self._policy.requires_manual_confirmation(call.name):
            return HarnessToolAuthorization.require_approval(
                f"Tool requires manual confirmation: {call.name}",
                metadata={"sideEffect": "manual-confirm-tool"},
            )
        if call.risk == "write" or self._policy.is_high_risk(call.name):
            return HarnessToolAuthorization.require_approval(
                f"Proposed high-risk action: {call.name}",
                metadata={"sideEffect": "proposed-write"},
            )
        return HarnessToolAuthorization.allow()

    def invoke_tool(
        self,
        request: HarnessRunRequest,
        call: HarnessToolCall,
    ) -> dict[str, Any]:
        del request
        tool = self._tools.get(call.name)
        if tool is None:
            raise HarnessToolFailure("TOOL_NOT_FOUND", f"Tool not found: {call.name}")
        return tool(dict(call.arguments))


class ConfigurableRestrictedReactWorker:
    def __init__(
        self,
        *,
        registry: Any,
        model_factory: Callable[[ReactWorkerConfig], ReactWorkerModel] | None = None,
        tools: dict[str, ReactTool] | None = None,
    ) -> None:
        self._registry = registry
        self._model_factory = model_factory or (lambda _config: DeterministicReactWorkerModel())
        self._tools = dict(tools or _default_tools())

    def run(self, task: TaskItem, message: str) -> WorkerResult:
        config = self._registry.lookup(task.task_type, task.worker_ref)
        if config is None:
            return WorkerResult(
                task_id=int(task.id or 0),
                worker_type=task.worker_type,
                status=TaskStatus.FAILED,
                operator_recommendation=f"No ReAct worker config for {task.task_type}/{task.worker_ref}",
                error={
                    "code": "REACT_WORKER_CONFIG_NOT_FOUND",
                    "message": f"No ReAct worker config for {task.task_type}/{task.worker_ref}",
                },
                events=[
                    _event(
                        "react_worker_failed",
                        {
                            "code": "REACT_WORKER_CONFIG_NOT_FOUND",
                            "taskType": task.task_type,
                            "workerRef": task.worker_ref,
                        },
                    )
                ],
            )
        try:
            return RestrictedReactWorker(
                config=config,
                model=self._model_factory(config),
                tools=self._tools,
            ).run(task, message)
        except UnsupportedReactToolPolicyError as exc:
            return WorkerResult(
                task_id=int(task.id or 0),
                worker_type=task.worker_type,
                status=TaskStatus.FAILED,
                operator_recommendation=str(exc),
                evidence={"workerRef": config.worker_ref, "workerConfigRefs": _worker_config_refs(config)},
                error={"code": "UNSUPPORTED_TOOL_POLICY_REF", "message": str(exc)},
                events=[
                    _event(
                        "react_worker_failed",
                        {
                            "code": "UNSUPPORTED_TOOL_POLICY_REF",
                            "toolPolicyRef": config.tool_policy_ref,
                        },
                    )
                ],
            )


def _event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": event_type,
        "source": "react_worker",
        "payload": {"schemaVersion": EVENT_SCHEMA_VERSION, "level": "L2", **_redact_payload(payload)},
    }


def _worker_config_refs(config: ReactWorkerConfig) -> dict[str, Any]:
    return {
        "workerRef": config.worker_ref,
        "workerType": config.worker_type,
        "modelPolicyRef": config.model_policy_ref,
        "promptRef": config.prompt_ref,
        "toolPolicyRef": config.tool_policy_ref,
        "toolRefs": list(config.allowed_tools),
        "riskPolicyRef": config.risk_policy_ref,
        "outputSchemaRef": config.output_schema_ref,
    }


def _proposed_action(task: TaskItem, call: ReactToolCall, *, side_effect: str = "proposed-write") -> dict[str, Any]:
    business_key = str(call.arguments.get("orderNo") or call.arguments.get("order_no") or task.business_key)
    return {
        "actionKey": f"{task.task_key}:{call.name}:{business_key}",
        "actionType": call.name,
        "title": f"Approve {call.name}",
        "payload": _redact_payload(dict(call.arguments)),
        "sideEffect": side_effect,
        "idempotencyKey": _react_idempotency_key(task, call, business_key),
    }


def _structured_observation(call: ReactToolCall, observation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": OBSERVATION_SCHEMA_VERSION,
        "tool": call.name,
        "sideEffect": "read-only",
        "summary": _observation_summary(observation),
    }


def _structured_final(action: ReactModelAction, iteration: int) -> dict[str, Any]:
    return {
        "schemaVersion": FINAL_SCHEMA_VERSION,
        "iteration": iteration,
        "hasOperatorRecommendation": bool(action.operator_recommendation),
        "hasCustomerReplyDraft": bool(action.customer_reply_draft),
    }


def _observation_summary(observation: dict[str, Any]) -> dict[str, Any]:
    return {key: str(_redact_payload(value))[:120] for key, value in observation.items()}


def _redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in _SECRET_KEYS:
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = _redact_payload(item)
        return redacted
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    return value


def _react_idempotency_key(task: TaskItem, call: ReactToolCall, business_key: str) -> str:
    raw = f"{task.session_id}:{task.id}:{task.task_key}:{call.name}:{business_key}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"react:{task.task_type}:{task.task_key}:{call.name}:{digest}"


def _customer_worker_result(
    *,
    task: TaskItem,
    config: ReactWorkerConfig,
    result: HarnessRunResult,
) -> WorkerResult:
    iterations = max((event.iteration or 0 for event in result.events), default=0)
    events = _customer_events_from_harness(task=task, config=config, result=result)
    evidence = {
        "workerRef": config.worker_ref,
        "iterations": iterations,
        "workerConfigRefs": _worker_config_refs(config),
    }

    if result.status is HarnessRunStatus.COMPLETED:
        action = ReactModelAction.final(
            operator_recommendation=str(result.output.get("operatorRecommendation") or ""),
            customer_reply_draft=str(result.output.get("customerReplyDraft") or ""),
        )
        evidence["structuredOutput"] = _structured_final(action, iterations)
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.COMPLETED,
            operator_recommendation=action.operator_recommendation,
            customer_reply_draft=action.customer_reply_draft,
            evidence=evidence,
            events=events,
        )

    if result.status is HarnessRunStatus.WAITING_APPROVAL and result.terminal_tool_call is not None:
        call = _customer_tool_call(result.terminal_tool_call)
        side_effect = str((result.authorization.metadata if result.authorization else {}).get("sideEffect") or "proposed-write")
        action_payload = _proposed_action(task, call, side_effect=side_effect)
        evidence["sideEffect"] = side_effect
        if side_effect == "manual-confirm-tool":
            recommendation = f"Tool requires manual confirmation: {call.name}"
            reply = "该动作需要人工确认后才能继续。"
        else:
            recommendation = f"Proposed high-risk action: {call.name}"
            reply = "该动作需要人工确认后才能执行。"
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.WAITING,
            operator_recommendation=recommendation,
            customer_reply_draft=reply,
            proposed_actions=[action_payload],
            evidence=evidence,
            events=events,
        )

    code = result.error_code or "REACT_WORKER_FAILED"
    message = _customer_harness_error_message(result)
    return WorkerResult(
        task_id=int(task.id or 0),
        worker_type=task.worker_type,
        status=TaskStatus.FAILED,
        operator_recommendation=message,
        evidence=evidence,
        events=events,
        error={"code": code, "message": message},
    )


def _customer_events_from_harness(
    *,
    task: TaskItem,
    config: ReactWorkerConfig,
    result: HarnessRunResult,
) -> list[dict[str, Any]]:
    observations = {item.tool_call.call_id: item for item in result.observations}
    calls = {item.tool_call.call_id: item.tool_call for item in result.observations}
    if result.terminal_tool_call is not None:
        calls[result.terminal_tool_call.call_id] = result.terminal_tool_call

    events: list[dict[str, Any]] = []
    for event in result.events:
        call = calls.get(event.tool_call_id or "")
        observation = observations.get(event.tool_call_id or "")
        if event.type == "harness.started":
            events.append(_event("react_worker_started", {"taskKey": task.task_key, "workerRef": task.worker_ref}))
        elif event.type == "harness.iteration.started":
            events.append(_event("react_iteration_started", {"iteration": event.iteration, "phase": "plan"}))
        elif event.type == "harness.tool.started" and call is not None:
            events.append(
                _event(
                    "react_tool_call_started",
                    {"iteration": event.iteration, "tool": call.name, "risk": call.risk},
                )
            )
        elif event.type == "harness.tool.completed" and call is not None and observation is not None:
            events.append(
                _event(
                    "react_tool_call_completed",
                    {
                        "iteration": event.iteration,
                        "tool": call.name,
                        "observationKeys": sorted(observation.output.keys()),
                    },
                )
            )
        elif event.type == "harness.observation.recorded" and call is not None and observation is not None:
            events.append(
                _event(
                    "react_observation_recorded",
                    {
                        "iteration": event.iteration,
                        "tool": call.name,
                        "observation": _structured_observation(_customer_tool_call(call), observation.output),
                    },
                )
            )
        elif event.type == "harness.tool.denied" and call is not None:
            events.append(
                _event(
                    "react_tool_call_started",
                    {"iteration": event.iteration, "tool": call.name, "risk": call.risk},
                )
            )
            events.append(_event("react_tool_call_failed", {"tool": call.name, "reason": "not_allowed"}))
        elif event.type == "harness.tool.failed" and call is not None:
            events.append(_event("react_tool_call_failed", {"tool": call.name, "reason": "missing_tool"}))
        elif event.type == "harness.approval.required" and call is not None:
            react_call = _customer_tool_call(call)
            side_effect = str(event.payload.get("sideEffect") or "proposed-write")
            action_payload = _proposed_action(task, react_call, side_effect=side_effect)
            events.append(
                _event(
                    "react_tool_call_started",
                    {"iteration": event.iteration, "tool": call.name, "risk": call.risk},
                )
            )
            payload: dict[str, Any] = {"proposedAction": action_payload["actionKey"]}
            if side_effect == "manual-confirm-tool":
                payload["toolPolicyRef"] = config.tool_policy_ref
            events.append(_event("react_worker_completed", payload))
        elif event.type == "harness.completed":
            action = ReactModelAction.final(
                operator_recommendation=str(result.output.get("operatorRecommendation") or ""),
                customer_reply_draft=str(result.output.get("customerReplyDraft") or ""),
            )
            events.append(
                _event(
                    "react_structured_output_completed",
                    {
                        "iteration": event.iteration,
                        "hasOperatorRecommendation": bool(action.operator_recommendation),
                        "hasCustomerReplyDraft": bool(action.customer_reply_draft),
                    },
                )
            )
            events.append(_event("react_worker_completed", {"iteration": event.iteration}))
        elif event.type == "harness.failed":
            events.append(_event("react_worker_failed", {"code": result.error_code or "REACT_WORKER_FAILED"}))
    return events


def _customer_tool_call(call: HarnessToolCall) -> ReactToolCall:
    risk: Literal["read", "write"] = "write" if call.risk == "write" else "read"
    return ReactToolCall(name=call.name, arguments=dict(call.arguments), risk=risk)


def _customer_harness_error_message(result: HarnessRunResult) -> str:
    if result.error_code == "WORKER_TIMEOUT":
        return "Restricted ReAct worker timed out"
    if result.error_code == "MAX_ITERATIONS_EXCEEDED":
        return "Restricted ReAct worker hit max iterations"
    return result.error_message or "Restricted ReAct worker failed"


def default_restricted_react_worker(config: ReactWorkerConfig) -> RestrictedReactWorker:
    return RestrictedReactWorker(
        config=config,
        model=DeterministicReactWorkerModel(),
        tools=_default_tools(),
    )


def configurable_restricted_react_worker(registry: Any) -> ConfigurableRestrictedReactWorker:
    return ConfigurableRestrictedReactWorker(
        registry=registry,
        tools=_default_tools(),
    )


def _default_tools() -> dict[str, ReactTool]:
    return {"lookup_order": lambda args: {"orderNo": args.get("orderNo"), "status": "refundable"}}
