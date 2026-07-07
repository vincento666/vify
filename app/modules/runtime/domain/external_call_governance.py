from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import monotonic
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ExternalCallPolicy:
    timeout_ms: int = 30_000
    retry_count: int = 0
    breaker_failure_threshold: int = 3
    breaker_reset_ms: int = 60_000


@dataclass
class _BreakerState:
    failure_count: int = 0
    opened_at_ms: int | None = None


class ExternalCallGovernanceError(RuntimeError):
    def __init__(self, message: str, *, event_payload: dict[str, Any]) -> None:
        super().__init__(message)
        self.event_type = "workflow_node_external_call_failed"
        self.event_payload = event_payload


class ExternalCallGovernance:
    def __init__(self, *, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or monotonic
        self._breakers: dict[str, _BreakerState] = {}

    def run(
        self,
        *,
        call_type: str,
        provider_key: str,
        node_key: str,
        node_run_id: int | None,
        policy: ExternalCallPolicy,
        operation: Callable[[], T],
    ) -> T:
        normalized_call_type = str(call_type or "EXTERNAL").upper()
        normalized_provider_key = str(provider_key or normalized_call_type).strip() or normalized_call_type
        normalized_policy = _normalized_policy(policy)
        state = self._breakers.setdefault(normalized_provider_key, _BreakerState())
        if self._breaker_open(state, normalized_policy):
            raise self._error(
                call_type=normalized_call_type,
                provider_key=normalized_provider_key,
                node_key=node_key,
                node_run_id=node_run_id,
                policy=normalized_policy,
                error_kind="circuit_open",
                message=f"Circuit breaker open for {normalized_provider_key}",
                attempts=0,
                breaker_open=True,
            )
        if state.opened_at_ms is not None:
            state.failure_count = 0
            state.opened_at_ms = None

        attempts = 0
        last_error: BaseException | None = None
        max_attempts = normalized_policy.retry_count + 1
        for attempt_index in range(max_attempts):
            attempts = attempt_index + 1
            started_at_ms = self._now_ms()
            try:
                result = operation()
            except BaseException as exc:
                last_error = exc
                if attempt_index < max_attempts - 1:
                    continue
                break
            elapsed_ms = self._now_ms() - started_at_ms
            if elapsed_ms > normalized_policy.timeout_ms:
                last_error = TimeoutError(f"{normalized_call_type} call timed out after {elapsed_ms}ms")
                if attempt_index < max_attempts - 1:
                    continue
                break
            state.failure_count = 0
            state.opened_at_ms = None
            return result

        state.failure_count += attempts
        breaker_open = state.failure_count >= normalized_policy.breaker_failure_threshold
        if breaker_open:
            state.opened_at_ms = self._now_ms()
        error_kind = _error_kind(last_error)
        message = str(last_error or "External call failed")
        raise self._error(
            call_type=normalized_call_type,
            provider_key=normalized_provider_key,
            node_key=node_key,
            node_run_id=node_run_id,
            policy=normalized_policy,
            error_kind=error_kind,
            message=message,
            attempts=attempts,
            breaker_open=breaker_open,
        )

    def _breaker_open(self, state: _BreakerState, policy: ExternalCallPolicy) -> bool:
        if state.opened_at_ms is None:
            return False
        return self._now_ms() - state.opened_at_ms < policy.breaker_reset_ms

    def _now_ms(self) -> int:
        return int(self._clock() * 1000)

    def _error(
        self,
        *,
        call_type: str,
        provider_key: str,
        node_key: str,
        node_run_id: int | None,
        policy: ExternalCallPolicy,
        error_kind: str,
        message: str,
        attempts: int,
        breaker_open: bool,
    ) -> ExternalCallGovernanceError:
        return ExternalCallGovernanceError(
            message,
            event_payload={
                "callType": call_type,
                "providerKey": provider_key,
                "nodeKey": str(node_key or ""),
                "nodeRunId": node_run_id,
                "errorKind": error_kind,
                "message": message,
                "attempts": attempts,
                "timeoutMs": policy.timeout_ms,
                "retryCount": policy.retry_count,
                "breakerOpen": breaker_open,
            },
        )


def external_call_policy_from_config(config: Mapping[str, Any]) -> ExternalCallPolicy:
    timeout_ms = _timeout_ms(config)
    return ExternalCallPolicy(
        timeout_ms=timeout_ms,
        retry_count=_non_negative_int(config.get("retryCount") or config.get("retry_count"), default=0),
        breaker_failure_threshold=_positive_int(
            config.get("breakerFailureThreshold") or config.get("breaker_failure_threshold"),
            default=3,
        ),
        breaker_reset_ms=_positive_int(config.get("breakerResetMs") or config.get("breaker_reset_ms"), default=60_000),
    )


def _normalized_policy(policy: ExternalCallPolicy) -> ExternalCallPolicy:
    return ExternalCallPolicy(
        timeout_ms=max(1, int(policy.timeout_ms)),
        retry_count=max(0, int(policy.retry_count)),
        breaker_failure_threshold=max(1, int(policy.breaker_failure_threshold)),
        breaker_reset_ms=max(1, int(policy.breaker_reset_ms)),
    )


def _timeout_ms(config: Mapping[str, Any]) -> int:
    if config.get("timeoutMs") not in (None, ""):
        return _positive_int(config.get("timeoutMs"), default=30_000)
    if config.get("timeout_ms") not in (None, ""):
        return _positive_int(config.get("timeout_ms"), default=30_000)
    if config.get("timeout") not in (None, ""):
        return int(_positive_float(config.get("timeout"), default=30.0) * 1000)
    return 30_000


def _error_kind(exc: BaseException | None) -> str:
    if isinstance(exc, TimeoutError):
        return "timeout"
    name = exc.__class__.__name__.lower() if exc is not None else ""
    text = str(exc or "").lower()
    if "timeout" in name or "timed out" in text or "timeout" in text:
        return "timeout"
    return "provider_error"


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _non_negative_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _positive_float(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default
