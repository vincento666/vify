from __future__ import annotations

import hashlib
from dataclasses import dataclass
from time import monotonic
from typing import Any, Callable, Literal, Protocol

from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus, WorkerResult
from app.modules.customer_assistant.domain.tool_policy import ReactToolPolicy
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
    ) -> None:
        self._config = config
        self._model = model
        self._tools = dict(tools)
        self._policy = policy or ReactToolPolicy(allowed_tools=config.allowed_tools)

    def run(self, task: TaskItem, message: str) -> WorkerResult:
        started = monotonic()
        events = [_event("react_worker_started", {"taskKey": task.task_key, "workerRef": task.worker_ref})]
        observation: dict[str, Any] | None = None
        for iteration in range(1, self._config.max_iterations + 1):
            events.append(_event("react_iteration_started", {"iteration": iteration, "phase": "plan"}))
            action = self._model.next_action(
                task=task,
                message=message,
                observation=observation,
                iteration=iteration,
            )
            if action.kind == "final":
                events.append(
                    _event(
                        "react_structured_output_completed",
                        {
                            "iteration": iteration,
                            "hasOperatorRecommendation": bool(action.operator_recommendation),
                            "hasCustomerReplyDraft": bool(action.customer_reply_draft),
                        },
                    )
                )
                events.append(_event("react_worker_completed", {"iteration": iteration}))
                return WorkerResult(
                    task_id=int(task.id or 0),
                    worker_type=task.worker_type,
                    status=TaskStatus.COMPLETED,
                    operator_recommendation=action.operator_recommendation,
                    customer_reply_draft=action.customer_reply_draft,
                    evidence={
                        "workerRef": self._config.worker_ref,
                        "iterations": iteration,
                        "structuredOutput": _structured_final(action, iteration),
                    },
                    events=events,
                )
            if action.tool_call is None:
                return self._failed(task, events, "INVALID_MODEL_ACTION", "tool_call action missing tool call")

            call = action.tool_call
            events.append(
                _event(
                    "react_tool_call_started",
                    {"iteration": iteration, "tool": call.name, "risk": call.risk},
                )
            )
            if not self._policy.is_allowed(call.name):
                events.append(_event("react_tool_call_failed", {"tool": call.name, "reason": "not_allowed"}))
                return self._failed(task, events, "TOOL_NOT_ALLOWED", f"Tool not allowed: {call.name}")
            if call.risk == "write" or self._policy.is_high_risk(call.name):
                action_payload = _proposed_action(task, call)
                events.append(_event("react_worker_completed", {"proposedAction": action_payload["actionKey"]}))
                return WorkerResult(
                    task_id=int(task.id or 0),
                    worker_type=task.worker_type,
                    status=TaskStatus.WAITING,
                    operator_recommendation=f"Proposed high-risk action: {call.name}",
                    customer_reply_draft="该动作需要人工确认后才能执行。",
                    proposed_actions=[action_payload],
                    evidence={
                        "workerRef": self._config.worker_ref,
                        "iterations": iteration,
                        "sideEffect": "proposed-write",
                    },
                    events=events,
                )

            tool = self._tools.get(call.name)
            if tool is None:
                events.append(_event("react_tool_call_failed", {"tool": call.name, "reason": "missing_tool"}))
                return self._failed(task, events, "TOOL_NOT_FOUND", f"Tool not found: {call.name}")
            observation = tool(dict(call.arguments))
            events.append(
                _event(
                    "react_tool_call_completed",
                    {"iteration": iteration, "tool": call.name, "observationKeys": sorted(observation.keys())},
                )
            )
            events.append(
                _event(
                    "react_observation_recorded",
                    {
                        "iteration": iteration,
                        "tool": call.name,
                        "observation": _structured_observation(call, observation),
                    },
                )
            )
            if _timed_out(started, self._config.timeout_ms):
                return self._failed(task, events, "WORKER_TIMEOUT", "Restricted ReAct worker timed out")
        return self._failed(task, events, "MAX_ITERATIONS_EXCEEDED", "Restricted ReAct worker hit max iterations")

    def _failed(self, task: TaskItem, events: list[dict[str, Any]], code: str, message: str) -> WorkerResult:
        events.append(_event("react_worker_failed", {"code": code}))
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.FAILED,
            operator_recommendation=message,
            evidence={"workerRef": self._config.worker_ref},
            events=events,
            error={"code": code, "message": message},
        )


def _event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": event_type,
        "source": "react_worker",
        "payload": {"schemaVersion": EVENT_SCHEMA_VERSION, "level": "L2", **_redact_payload(payload)},
    }


def _proposed_action(task: TaskItem, call: ReactToolCall) -> dict[str, Any]:
    business_key = str(call.arguments.get("orderNo") or call.arguments.get("order_no") or task.business_key)
    return {
        "actionKey": f"{task.task_key}:{call.name}:{business_key}",
        "actionType": call.name,
        "title": f"Approve {call.name}",
        "payload": _redact_payload(dict(call.arguments)),
        "sideEffect": "proposed-write",
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


def _timed_out(started: float, timeout_ms: int) -> bool:
    return (monotonic() - started) * 1000 > timeout_ms


def default_restricted_react_worker(config: ReactWorkerConfig) -> RestrictedReactWorker:
    return RestrictedReactWorker(
        config=config,
        model=DeterministicReactWorkerModel(),
        tools={"lookup_order": lambda args: {"orderNo": args.get("orderNo"), "status": "refundable"}},
    )
