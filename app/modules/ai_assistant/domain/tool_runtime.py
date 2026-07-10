from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from hashlib import sha256
import json
from random import random
from time import perf_counter, time
from typing import Any, Callable, Protocol

from app.modules.ai_assistant.domain.tools import RiskLevel, ToolRegistry, ToolResult


SleepFn = Callable[[float], None]
JitterFn = Callable[[], float]
FallbackAdapter = Callable[[str, dict[str, Any], dict[str, Any]], ToolResult]


class ToolOperationLedger(Protocol):
    def create_or_get_tool_operation(self, **values: Any) -> tuple[dict[str, Any], bool]: ...

    def complete_tool_operation(
        self,
        operation_id: str,
        *,
        output_payload: dict[str, Any],
        response_hash: str | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ToolRunnerPolicy:
    max_attempts: int = 2
    initial_backoff_ms: int = 100
    backoff_multiplier: float = 2.0
    jitter_ms: int = 50
    circuit_failure_threshold: int = 3
    circuit_open_seconds: float = 30.0


@dataclass(frozen=True)
class ToolRunResult:
    tool_result: ToolResult
    duration_ms: int
    attempts: int
    idempotency_key: str
    events: list[dict[str, Any]]
    span: dict[str, Any]
    budget: dict[str, Any]
    operation_id: str = ""


@dataclass
class _CircuitState:
    failures: int = 0
    opened_at: float | None = None


@dataclass(frozen=True)
class _LedgerEntry:
    state: str
    tool_result: ToolResult | None = None
    error: dict[str, Any] | None = None


class ToolRunner:
    def __init__(
        self,
        registry: ToolRegistry,
        *,
        policy: ToolRunnerPolicy | None = None,
        fallback_adapters: dict[str, FallbackAdapter] | None = None,
        operation_ledger: ToolOperationLedger | None = None,
        sleep: SleepFn | None = None,
        jitter: JitterFn | None = None,
    ) -> None:
        self._registry = registry
        self._policy = policy or ToolRunnerPolicy()
        self._fallback_adapters = fallback_adapters or {}
        self._operation_ledger = operation_ledger
        self._sleep = sleep or _default_sleep
        self._jitter = jitter
        self._circuits: dict[str, _CircuitState] = {}
        self._ledger: dict[str, _LedgerEntry] = {}

    def run(self, tool_name: str, payload: dict[str, Any], *, idempotency_key: str = "") -> ToolRunResult:
        started = perf_counter()
        resolved_idempotency_key = idempotency_key or _stable_idempotency_key(tool_name, payload)
        events: list[dict[str, Any]] = []
        operation_id, replayed_operation = self._prepare_side_effect_operation(
            tool_name=tool_name,
            payload=payload,
            idempotency_key=resolved_idempotency_key,
        )
        if replayed_operation is not None and replayed_operation.get("status") == "COMPLETED":
            completed = dict(replayed_operation.get("output_payload") or {})
            tool_result = ToolResult(
                status=str(completed.get("status") or "COMPLETED"),
                output=dict(completed.get("output") or {}),
            )
            duration_ms = _elapsed_ms(started)
            events.append(
                {
                    "type": "tool.idempotency_replayed",
                    "payload": {
                        "toolName": tool_name,
                        "idempotencyKey": resolved_idempotency_key,
                        "operationId": operation_id,
                    },
                }
            )
            return ToolRunResult(
                tool_result=tool_result,
                duration_ms=duration_ms,
                attempts=0,
                idempotency_key=resolved_idempotency_key,
                events=events,
                span=_span(
                    tool_name=tool_name,
                    status="OK",
                    duration_ms=duration_ms,
                    attempts=0,
                    idempotency_key=resolved_idempotency_key,
                )
                | {"idempotencyReplayed": True, "operationId": operation_id},
                budget=_budget(attempts=0, duration_ms=duration_ms, retries=0),
                operation_id=operation_id,
            )
        ledger_entry = self._ledger.get(resolved_idempotency_key)
        if ledger_entry is not None:
            if ledger_entry.state == "COMPLETED" and ledger_entry.tool_result is not None:
                duration_ms = _elapsed_ms(started)
                events.append(
                    {
                        "type": "tool.idempotency_replayed",
                        "payload": {"toolName": tool_name, "idempotencyKey": resolved_idempotency_key},
                    }
                )
                return ToolRunResult(
                    tool_result=ledger_entry.tool_result,
                    duration_ms=duration_ms,
                    attempts=0,
                    idempotency_key=resolved_idempotency_key,
                    events=events,
                    span=_span(
                        tool_name=tool_name,
                        status="OK",
                        duration_ms=duration_ms,
                        attempts=0,
                        idempotency_key=resolved_idempotency_key,
                    )
                    | {"idempotencyReplayed": True},
                    budget=_budget(attempts=0, duration_ms=duration_ms, retries=0),
                )
            if ledger_entry.state == "UNKNOWN":
                error = _error_payload(
                    code="TOOL_IDEMPOTENCY_UNCERTAIN",
                    message="A previous attempt with this idempotency key timed out and may still complete.",
                    error_type="idempotency_uncertain",
                    retriable=False,
                )
                events.append(
                    {
                        "type": "tool.idempotency_uncertain",
                        "payload": {"toolName": tool_name, "idempotencyKey": resolved_idempotency_key, "error": error},
                    }
                )
                return self._failed_result(
                    tool_name=tool_name,
                    payload=payload,
                    idempotency_key=resolved_idempotency_key,
                    attempts=0,
                    duration_ms=_elapsed_ms(started),
                    error=error,
                    events=events,
                )
        circuit = self._circuits.setdefault(tool_name, _CircuitState())
        if self._is_circuit_open(circuit):
            error = _error_payload(
                code="TOOL_CIRCUIT_OPEN",
                message=f"Circuit is open for tool {tool_name}",
                error_type="circuit_open",
                retriable=True,
            )
            events.append({"type": "tool.circuit_open", "payload": {"toolName": tool_name, "error": error}})
            return self._failed_result(
                tool_name=tool_name,
                payload=payload,
                idempotency_key=resolved_idempotency_key,
                attempts=0,
                duration_ms=_elapsed_ms(started),
                error=error,
                events=events,
            )

        manifest_timeout_ms = self._tool_timeout_ms(tool_name)
        max_attempts = max(1, int(self._policy.max_attempts))
        last_error: dict[str, Any] | None = None
        attempts = 0
        for attempt in range(1, max_attempts + 1):
            attempts = attempt
            dispatch_payload = _payload_with_runtime(
                payload,
                resolved_idempotency_key,
                attempt,
                operation_id=operation_id,
            )
            try:
                tool_result = self._dispatch_with_timeout(tool_name, dispatch_payload, manifest_timeout_ms)
            except Exception as exc:
                error = _classify_error(exc)
                last_error = error
                events.append(
                    {
                        "type": "tool.call_attempt_failed",
                        "payload": {"toolName": tool_name, "attempt": attempt, "error": error},
                    }
                )
                if error.get("code") == "TOOL_TIMEOUT":
                    break
                if attempt < max_attempts and bool(error.get("retriable")):
                    delay_seconds = self._backoff_seconds(attempt)
                    events.append(
                        {
                            "type": "tool.retry_scheduled",
                            "payload": {
                                "toolName": tool_name,
                                "attempt": attempt,
                                "nextAttempt": attempt + 1,
                                "delayMs": int(delay_seconds * 1000),
                                "error": error,
                            },
                        }
                    )
                    self._sleep(delay_seconds)
                    continue
                break
            else:
                self._reset_circuit(circuit)
                duration_ms = _elapsed_ms(started)
                events.append(
                    {
                        "type": "tool.call_completed",
                        "payload": {"toolName": tool_name, "status": tool_result.status, "attempts": attempts},
                    }
                )
                result = ToolRunResult(
                    tool_result=tool_result,
                    duration_ms=duration_ms,
                    attempts=attempts,
                    idempotency_key=resolved_idempotency_key,
                    events=events,
                    span=_span(
                        tool_name=tool_name,
                        status="OK",
                        duration_ms=duration_ms,
                        attempts=attempts,
                        idempotency_key=resolved_idempotency_key,
                    )
                    | ({"operationId": operation_id} if operation_id else {}),
                    budget=_budget(attempts=attempts, duration_ms=duration_ms, retries=max(0, attempts - 1)),
                    operation_id=operation_id,
                )
                if operation_id and self._operation_ledger is not None:
                    self._operation_ledger.complete_tool_operation(
                        operation_id,
                        output_payload={"status": tool_result.status, "output": tool_result.output},
                        response_hash=_response_hash(tool_result.output),
                    )
                self._ledger[resolved_idempotency_key] = _LedgerEntry(state="COMPLETED", tool_result=tool_result)
                return result

        error = last_error or _error_payload(
            code="TOOL_RUNTIME_ERROR",
            message=f"Tool {tool_name} failed without a captured error",
            error_type="unknown",
            retriable=True,
        )
        self._record_failure(circuit)
        if error.get("code") == "TOOL_TIMEOUT":
            self._ledger[resolved_idempotency_key] = _LedgerEntry(state="UNKNOWN", error=error)
            return self._failed_result(
                tool_name=tool_name,
                payload=payload,
                idempotency_key=resolved_idempotency_key,
                attempts=attempts,
                duration_ms=_elapsed_ms(started),
                error=error,
                events=events,
            )
        fallback = self._fallback_adapters.get(tool_name)
        if fallback is not None:
            try:
                fallback_result = fallback(tool_name, payload, error)
            except Exception as fallback_exc:
                error = _classify_error(fallback_exc)
            else:
                duration_ms = _elapsed_ms(started)
                events.append(
                    {
                        "type": "tool.fallback_used",
                        "payload": {"toolName": tool_name, "status": fallback_result.status, "sourceError": error},
                    }
                )
                result = ToolRunResult(
                    tool_result=fallback_result,
                    duration_ms=duration_ms,
                    attempts=attempts,
                    idempotency_key=resolved_idempotency_key,
                    events=events,
                    span=_span(
                        tool_name=tool_name,
                        status="OK",
                        duration_ms=duration_ms,
                        attempts=attempts,
                        idempotency_key=resolved_idempotency_key,
                        fallback=True,
                    ),
                    budget=_budget(attempts=attempts, duration_ms=duration_ms, retries=max(0, attempts - 1)),
                )
                self._ledger[resolved_idempotency_key] = _LedgerEntry(state="COMPLETED", tool_result=fallback_result)
                return result

        return self._failed_result(
            tool_name=tool_name,
            payload=payload,
            idempotency_key=resolved_idempotency_key,
            attempts=attempts,
            duration_ms=_elapsed_ms(started),
            error=error,
            events=events,
        )

    def _dispatch_with_timeout(self, tool_name: str, payload: dict[str, Any], timeout_ms: int) -> ToolResult:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._registry.dispatch, tool_name, payload)
        try:
            return future.result(timeout=max(timeout_ms, 1) / 1000)
        except TimeoutError as exc:
            future.cancel()
            raise exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _prepare_side_effect_operation(
        self,
        *,
        tool_name: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> tuple[str, dict[str, Any] | None]:
        if self._operation_ledger is None:
            return "", None
        manifest = self._registry.get_manifest(tool_name)
        if manifest.risk_level == RiskLevel.READ:
            return "", None
        runtime = dict(payload.get("_aiAssistantRuntime") or {})
        session_id = int(runtime.get("sessionId") or 0)
        run_id = int(runtime.get("runId") or 0)
        plan_step_id = str(runtime.get("planStepId") or tool_name)
        operation_id = _operation_id(
            session_id=session_id,
            run_id=run_id,
            plan_step_id=plan_step_id,
            tool_name=tool_name,
            effect_class="SIDE_EFFECT",
            payload=payload,
            idempotency_key=idempotency_key,
        )
        operation, existed = self._operation_ledger.create_or_get_tool_operation(
            operation_id=operation_id,
            session_id=session_id,
            run_id=run_id,
            plan_step_id=plan_step_id,
            tool_name=tool_name,
            effect_class="SIDE_EFFECT",
            idempotency_key=idempotency_key,
            request_hash=_request_hash(payload),
        )
        return operation_id, operation if existed else None

    def _tool_timeout_ms(self, tool_name: str) -> int:
        try:
            return int(self._registry.get_manifest(tool_name).timeout_ms)
        except Exception:
            return 1000

    def _backoff_seconds(self, failed_attempt: int) -> float:
        base_ms = self._policy.initial_backoff_ms * (self._policy.backoff_multiplier ** max(0, failed_attempt - 1))
        if self._jitter is not None:
            jitter_seconds = max(0.0, float(self._jitter()))
        else:
            jitter_seconds = (random() * max(0, self._policy.jitter_ms)) / 1000
        return max(0.0, (base_ms / 1000) + jitter_seconds)

    def _is_circuit_open(self, circuit: _CircuitState) -> bool:
        if circuit.opened_at is None:
            return False
        if time() - circuit.opened_at >= self._policy.circuit_open_seconds:
            circuit.failures = 0
            circuit.opened_at = None
            return False
        return True

    def _record_failure(self, circuit: _CircuitState) -> None:
        circuit.failures += 1
        if circuit.failures >= self._policy.circuit_failure_threshold:
            circuit.opened_at = time()

    def _reset_circuit(self, circuit: _CircuitState) -> None:
        circuit.failures = 0
        circuit.opened_at = None

    def _failed_result(
        self,
        *,
        tool_name: str,
        payload: dict[str, Any],
        idempotency_key: str,
        attempts: int,
        duration_ms: int,
        error: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> ToolRunResult:
        observation = structured_tool_error_observation(
            tool_name=tool_name,
            payload=payload,
            error=error,
            attempts=attempts,
            idempotency_key=idempotency_key,
        )
        events.append({"type": "tool.error_observation", "payload": {"toolName": tool_name, "observation": observation}})
        return ToolRunResult(
            tool_result=ToolResult(
                status="FAILED",
                output={
                    "status": "FAILED",
                    "message": error["message"],
                    "error": error,
                    "observation": observation,
                },
            ),
            duration_ms=duration_ms,
            attempts=attempts,
            idempotency_key=idempotency_key,
            events=events,
            span=_span(
                tool_name=tool_name,
                status="ERROR",
                duration_ms=duration_ms,
                attempts=attempts,
                idempotency_key=idempotency_key,
                error=error,
            ),
            budget=_budget(attempts=attempts, duration_ms=duration_ms, retries=max(0, attempts - 1)),
        )


def structured_tool_error_observation(
    *,
    tool_name: str,
    payload: dict[str, Any],
    error: dict[str, Any],
    attempts: int,
    idempotency_key: str,
) -> dict[str, Any]:
    return {
        "kind": "tool_error",
        "toolName": tool_name,
        "toolInput": _public_tool_input(payload),
        "idempotencyKey": idempotency_key,
        "attempts": attempts,
        "error": error,
        "retriable": bool(error.get("retriable")),
        "modelVisible": True,
        "suggestedActions": [
            "retry_with_backoff",
            "change_arguments",
            "choose_alternative_tool",
            "degrade_or_revise_plan",
        ],
    }


def _payload_with_runtime(
    payload: dict[str, Any],
    idempotency_key: str,
    attempt: int,
    *,
    operation_id: str = "",
) -> dict[str, Any]:
    runtime_payload = dict(payload.get("_toolRuntime") or {})
    runtime_payload.update({"idempotencyKey": idempotency_key, "attempt": attempt})
    if operation_id:
        runtime_payload["operationId"] = operation_id
    return {**payload, "_toolRuntime": runtime_payload}


def _public_tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if not str(key).startswith("_")}


def _classify_error(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, TimeoutError):
        return _error_payload(
            code="TOOL_TIMEOUT",
            message="Tool execution timed out",
            error_type=type(exc).__name__,
            retriable=True,
        )
    if isinstance(exc, KeyError):
        return _error_payload(
            code="TOOL_NOT_FOUND",
            message=str(exc),
            error_type=type(exc).__name__,
            retriable=False,
        )
    message = str(exc) or type(exc).__name__
    lowered = message.lower()
    if "rate" in lowered and "limit" in lowered:
        code = "TOOL_RATE_LIMIT"
    else:
        code = "TOOL_RUNTIME_ERROR"
    return _error_payload(code=code, message=message, error_type=type(exc).__name__, retriable=True)


def _error_payload(*, code: str, message: str, error_type: str, retriable: bool) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "type": error_type,
        "retriable": retriable,
    }


def _span(
    *,
    tool_name: str,
    status: str,
    duration_ms: int,
    attempts: int,
    idempotency_key: str,
    fallback: bool = False,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    span = {
        "name": "tool.call",
        "kind": "tool",
        "toolName": tool_name,
        "status": status,
        "durationMs": duration_ms,
        "attempts": attempts,
        "idempotencyKey": idempotency_key,
        "fallback": fallback,
    }
    if error is not None:
        span["error"] = error
    return span


def _budget(*, attempts: int, duration_ms: int, retries: int) -> dict[str, Any]:
    return {
        "attempts": attempts,
        "retries": retries,
        "durationMs": duration_ms,
        "costUnits": attempts,
    }


def _stable_idempotency_key(tool_name: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps({"toolName": tool_name, "payload": payload}, sort_keys=True, ensure_ascii=True)
    return f"{tool_name}:{sha256(encoded.encode('utf-8')).hexdigest()[:24]}"


def _operation_id(
    *,
    session_id: int,
    run_id: int,
    plan_step_id: str,
    tool_name: str,
    effect_class: str,
    payload: dict[str, Any],
    idempotency_key: str,
) -> str:
    encoded = _canonical_json(
        {
            "version": "v1",
            "sessionId": session_id,
            "runId": run_id,
            "planStepId": plan_step_id,
            "toolName": tool_name,
            "effectClass": effect_class,
            "toolArgs": _redacted_tool_args(payload),
            "idempotencyKey": idempotency_key,
        }
    )
    return f"op:{sha256(encoded.encode('utf-8')).hexdigest()}"


def _request_hash(payload: dict[str, Any]) -> str:
    return sha256(_canonical_json(_redacted_tool_args(payload)).encode("utf-8")).hexdigest()


def _response_hash(output: dict[str, Any]) -> str:
    return sha256(_canonical_json(output).encode("utf-8")).hexdigest()


def _redacted_tool_args(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: _redact_value(key, value) for key, value in _public_tool_input(payload).items()}


def _redact_value(key: str, value: Any) -> Any:
    if key.lower() in {"api_key", "apikey", "authorization", "password", "secret", "token"}:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(child_key): _redact_value(str(child_key), child_value) for child_key, child_value in value.items()}
    if isinstance(value, list):
        return [_redact_value(key, item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str)


def _elapsed_ms(started: float) -> int:
    return max(1, int((perf_counter() - started) * 1000))


def _default_sleep(seconds: float) -> None:
    from time import sleep

    sleep(seconds)
