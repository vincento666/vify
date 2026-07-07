from __future__ import annotations

import pytest

from app.modules.runtime.domain.concurrency_limits import RuntimeConcurrencyGate, RuntimeConcurrencyLimits
from app.modules.runtime.domain.external_call_governance import (
    ExternalCallGovernance,
    ExternalCallGovernanceError,
    ExternalCallPolicy,
)


def test_slow_external_calls_trigger_deadline_breaker_and_provider_backpressure() -> None:
    clock = _FakeClock()
    governance = ExternalCallGovernance(clock=clock.now)

    with pytest.raises(ExternalCallGovernanceError) as llm_error:
        governance.run(
            call_type="LLM",
            provider_key="llm:slow-openrouter",
            node_key="llm_1",
            node_run_id=221_800_001,
            policy=ExternalCallPolicy(timeout_ms=100, retry_count=1, breaker_failure_threshold=2),
            operation=lambda: clock.advance_and_return(60, "too late"),
        )

    assert llm_error.value.event_payload["errorKind"] == "timeout"
    assert llm_error.value.event_payload["attempts"] == 2
    assert llm_error.value.event_payload["breakerOpen"] is True

    with pytest.raises(ExternalCallGovernanceError) as open_breaker:
        governance.run(
            call_type="LLM",
            provider_key="llm:slow-openrouter",
            node_key="llm_2",
            node_run_id=221_800_002,
            policy=ExternalCallPolicy(timeout_ms=100, retry_count=1, breaker_failure_threshold=2),
            operation=lambda: clock.advance_and_return(60, "should not run"),
        )

    assert open_breaker.value.event_payload["errorKind"] == "circuit_open"
    assert open_breaker.value.event_payload["attempts"] == 0

    with pytest.raises(ExternalCallGovernanceError) as api_error:
        governance.run(
            call_type="API",
            provider_key="api:slow-resource",
            node_key="api_1",
            node_run_id=221_800_003,
            policy=ExternalCallPolicy(timeout_ms=100, retry_count=0, breaker_failure_threshold=1),
            operation=lambda: clock.advance_and_return(120, {"ok": True}),
        )

    assert api_error.value.event_payload["errorKind"] == "timeout"
    assert api_error.value.event_payload["attempts"] == 1
    assert api_error.value.event_payload["breakerOpen"] is True

    gate = RuntimeConcurrencyGate(RuntimeConcurrencyLimits(provider_active_limit=1))
    decision = gate.decide(
        [
            {
                "status": "RUNNING",
                "owner_type": "WORKFLOW",
                "owner_id": 2218,
                "lease_owner": "worker-a",
                "payload": {"tenantId": "local", "providerKeys": ["llm:slow-openrouter"]},
            }
        ],
        owner_type="WORKFLOW",
        owner_id=2218,
        tenant_id="local",
        provider_keys=["llm:slow-openrouter"],
    )

    assert decision.level == "provider"
    assert decision.status == "degraded"
    assert decision.admitted is False


class _FakeClock:
    def __init__(self) -> None:
        self._seconds = 0.0

    def now(self) -> float:
        return self._seconds

    def advance_and_return(self, seconds: float, value: object) -> object:
        self._seconds += seconds
        return value
