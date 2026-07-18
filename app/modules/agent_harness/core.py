from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from time import monotonic
from typing import Any, Protocol


class HarnessRunStatus(StrEnum):
    COMPLETED = "COMPLETED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    FAILED = "FAILED"


@dataclass(frozen=True)
class HarnessRunRequest:
    run_id: str
    input: Any
    max_iterations: int
    timeout_ms: int | None = None

    def __post_init__(self) -> None:
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        if self.timeout_ms is not None and self.timeout_ms < 1:
            raise ValueError("timeout_ms must be at least 1")


@dataclass(frozen=True)
class HarnessToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]
    risk: str = "read"


class HarnessToolAuthorizationEffect(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


@dataclass(frozen=True)
class HarnessToolAuthorization:
    effect: HarnessToolAuthorizationEffect
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def allow(cls) -> HarnessToolAuthorization:
        return cls(effect=HarnessToolAuthorizationEffect.ALLOW)

    @classmethod
    def deny(cls, reason: str = "") -> HarnessToolAuthorization:
        return cls(effect=HarnessToolAuthorizationEffect.DENY, reason=reason)

    @classmethod
    def require_approval(
        cls,
        reason: str = "",
        *,
        metadata: dict[str, Any] | None = None,
    ) -> HarnessToolAuthorization:
        return cls(
            effect=HarnessToolAuthorizationEffect.REQUIRE_APPROVAL,
            reason=reason,
            metadata=dict(metadata or {}),
        )


@dataclass(frozen=True)
class HarnessDecision:
    tool_calls: tuple[HarnessToolCall, ...] = ()
    final_output: dict[str, Any] | None = None

    @classmethod
    def request_tools(cls, *tool_calls: HarnessToolCall) -> HarnessDecision:
        if not tool_calls:
            raise ValueError("at least one tool call is required")
        return cls(tool_calls=tuple(tool_calls))

    @classmethod
    def finish(cls, output: dict[str, Any]) -> HarnessDecision:
        return cls(final_output=dict(output))


@dataclass(frozen=True)
class HarnessObservation:
    tool_call: HarnessToolCall
    output: dict[str, Any]


@dataclass(frozen=True)
class HarnessEvent:
    type: str
    iteration: int | None = None
    tool_call_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HarnessRunResult:
    status: HarnessRunStatus
    output: dict[str, Any]
    observations: tuple[HarnessObservation, ...]
    events: tuple[HarnessEvent, ...]
    error_code: str | None = None
    error_message: str | None = None
    terminal_tool_call: HarnessToolCall | None = None
    authorization: HarnessToolAuthorization | None = None


@dataclass(frozen=True)
class HarnessToolBatchResult:
    observations: tuple[HarnessObservation, ...] = ()
    terminal_status: HarnessRunStatus | None = None
    terminal_output: dict[str, Any] = field(default_factory=dict)
    terminal_tool_call: HarnessToolCall | None = None
    authorization: HarnessToolAuthorization | None = None
    error_code: str | None = None
    error_message: str | None = None


class HarnessToolFailure(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class HarnessProfile(Protocol):
    def plan(
        self,
        request: HarnessRunRequest,
        observations: tuple[HarnessObservation, ...],
        iteration: int,
    ) -> HarnessDecision: ...

    def authorize_tool(
        self,
        request: HarnessRunRequest,
        call: HarnessToolCall,
    ) -> HarnessToolAuthorization: ...

    def invoke_tool(
        self,
        request: HarnessRunRequest,
        call: HarnessToolCall,
    ) -> dict[str, Any]: ...


def _authorization_terminal_result(
    *,
    call: HarnessToolCall,
    authorization: HarnessToolAuthorization,
    iteration: int,
    observations: list[HarnessObservation],
    events: list[HarnessEvent],
) -> HarnessRunResult | None:
    if authorization.effect is HarnessToolAuthorizationEffect.ALLOW:
        return None
    if authorization.effect is HarnessToolAuthorizationEffect.DENY:
        events.append(
            HarnessEvent(
                type="harness.tool.denied",
                iteration=iteration,
                tool_call_id=call.call_id,
                payload={"tool": call.name, "reason": authorization.reason},
            )
        )
        events.append(
            HarnessEvent(
                type="harness.failed",
                iteration=iteration,
                tool_call_id=call.call_id,
            )
        )
        return HarnessRunResult(
            status=HarnessRunStatus.FAILED,
            output={},
            observations=tuple(observations),
            events=tuple(events),
            error_code="TOOL_NOT_ALLOWED",
            error_message=authorization.reason or f"Tool not allowed: {call.name}",
            terminal_tool_call=call,
            authorization=authorization,
        )
    events.append(
        HarnessEvent(
            type="harness.approval.required",
            iteration=iteration,
            tool_call_id=call.call_id,
            payload={"tool": call.name, **authorization.metadata},
        )
    )
    return HarnessRunResult(
        status=HarnessRunStatus.WAITING_APPROVAL,
        output={},
        observations=tuple(observations),
        events=tuple(events),
        terminal_tool_call=call,
        authorization=authorization,
    )


class AgentHarness:
    def execute(
        self,
        request: HarnessRunRequest,
        profile: HarnessProfile,
    ) -> HarnessRunResult:
        started = monotonic()
        observations: list[HarnessObservation] = []
        events = [HarnessEvent(type="harness.started")]

        for iteration in range(1, request.max_iterations + 1):
            events.append(HarnessEvent(type="harness.iteration.started", iteration=iteration))
            decision = profile.plan(request, tuple(observations), iteration)
            if decision.final_output is not None:
                events.append(HarnessEvent(type="harness.completed", iteration=iteration))
                return HarnessRunResult(
                    status=HarnessRunStatus.COMPLETED,
                    output=decision.final_output,
                    observations=tuple(observations),
                    events=tuple(events),
                )
            if not decision.tool_calls:
                events.append(HarnessEvent(type="harness.failed", iteration=iteration))
                return HarnessRunResult(
                    status=HarnessRunStatus.FAILED,
                    output={},
                    observations=tuple(observations),
                    events=tuple(events),
                    error_code="INVALID_MODEL_ACTION",
                    error_message="tool_call action missing tool call",
                )

            batch_invoker = getattr(profile, "invoke_tools", None)
            if callable(batch_invoker):
                authorizations = tuple(profile.authorize_tool(request, call) for call in decision.tool_calls)
                for call, authorization in zip(decision.tool_calls, authorizations, strict=True):
                    terminal_result = _authorization_terminal_result(
                        call=call,
                        authorization=authorization,
                        iteration=iteration,
                        observations=observations,
                        events=events,
                    )
                    if terminal_result is not None:
                        return terminal_result
                for call in decision.tool_calls:
                    events.append(
                        HarnessEvent(
                            type="harness.tool.started",
                            iteration=iteration,
                            tool_call_id=call.call_id,
                            payload={"tool": call.name},
                        )
                    )
                batch_result = batch_invoker(request, decision.tool_calls)
                for observation in batch_result.observations:
                    observations.append(observation)
                    events.append(
                        HarnessEvent(
                            type="harness.tool.completed",
                            iteration=iteration,
                            tool_call_id=observation.tool_call.call_id,
                            payload={"tool": observation.tool_call.name},
                        )
                    )
                    events.append(
                        HarnessEvent(
                            type="harness.observation.recorded",
                            iteration=iteration,
                            tool_call_id=observation.tool_call.call_id,
                            payload={"tool": observation.tool_call.name},
                        )
                    )
                if batch_result.terminal_status is not None:
                    terminal_event = (
                        "harness.completed"
                        if batch_result.terminal_status is HarnessRunStatus.COMPLETED
                        else (
                            "harness.approval.required"
                            if batch_result.terminal_status is HarnessRunStatus.WAITING_APPROVAL
                            else "harness.failed"
                        )
                    )
                    events.append(
                        HarnessEvent(
                            type=terminal_event,
                            iteration=iteration,
                            tool_call_id=(
                                batch_result.terminal_tool_call.call_id
                                if batch_result.terminal_tool_call is not None
                                else None
                            ),
                        )
                    )
                    return HarnessRunResult(
                        status=batch_result.terminal_status,
                        output=batch_result.terminal_output,
                        observations=tuple(observations),
                        events=tuple(events),
                        error_code=batch_result.error_code,
                        error_message=batch_result.error_message,
                        terminal_tool_call=batch_result.terminal_tool_call,
                        authorization=batch_result.authorization,
                    )
                if request.timeout_ms is not None and (monotonic() - started) * 1000 > request.timeout_ms:
                    events.append(HarnessEvent(type="harness.failed", iteration=iteration))
                    return HarnessRunResult(
                        status=HarnessRunStatus.FAILED,
                        output={},
                        observations=tuple(observations),
                        events=tuple(events),
                        error_code="WORKER_TIMEOUT",
                        error_message="Agent Harness execution timed out",
                    )
                continue

            for call in decision.tool_calls:
                authorization = profile.authorize_tool(request, call)
                terminal_result = _authorization_terminal_result(
                    call=call,
                    authorization=authorization,
                    iteration=iteration,
                    observations=observations,
                    events=events,
                )
                if terminal_result is not None:
                    return terminal_result
                events.append(
                    HarnessEvent(
                        type="harness.tool.started",
                        iteration=iteration,
                        tool_call_id=call.call_id,
                        payload={"tool": call.name},
                    )
                )
                try:
                    output = profile.invoke_tool(request, call)
                except HarnessToolFailure as exc:
                    events.append(
                        HarnessEvent(
                            type="harness.tool.failed",
                            iteration=iteration,
                            tool_call_id=call.call_id,
                            payload={"tool": call.name, "code": exc.code},
                        )
                    )
                    events.append(
                        HarnessEvent(
                            type="harness.failed",
                            iteration=iteration,
                            tool_call_id=call.call_id,
                        )
                    )
                    return HarnessRunResult(
                        status=HarnessRunStatus.FAILED,
                        output={},
                        observations=tuple(observations),
                        events=tuple(events),
                        error_code=exc.code,
                        error_message=exc.message,
                        terminal_tool_call=call,
                        authorization=authorization,
                    )
                events.append(
                    HarnessEvent(
                        type="harness.tool.completed",
                        iteration=iteration,
                        tool_call_id=call.call_id,
                        payload={"tool": call.name},
                    )
                )
                observations.append(HarnessObservation(tool_call=call, output=dict(output)))
                events.append(
                    HarnessEvent(
                        type="harness.observation.recorded",
                        iteration=iteration,
                        tool_call_id=call.call_id,
                        payload={"tool": call.name},
                    )
                )
                if request.timeout_ms is not None and (monotonic() - started) * 1000 > request.timeout_ms:
                    events.append(
                        HarnessEvent(
                            type="harness.failed",
                            iteration=iteration,
                            tool_call_id=call.call_id,
                        )
                    )
                    return HarnessRunResult(
                        status=HarnessRunStatus.FAILED,
                        output={},
                        observations=tuple(observations),
                        events=tuple(events),
                        error_code="WORKER_TIMEOUT",
                        error_message="Agent Harness execution timed out",
                        terminal_tool_call=call,
                        authorization=authorization,
                    )

        events.append(HarnessEvent(type="harness.failed", iteration=request.max_iterations))
        return HarnessRunResult(
            status=HarnessRunStatus.FAILED,
            output={},
            observations=tuple(observations),
            events=tuple(events),
            error_code="MAX_ITERATIONS_EXCEEDED",
            error_message="Agent Harness reached max iterations",
        )
