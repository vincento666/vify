from __future__ import annotations

import pytest

from app.modules.runtime.domain.concurrency_limits import RuntimeConcurrencyGate, RuntimeConcurrencyLimits


@pytest.mark.parametrize(
    ("limits", "rows", "expected_level", "expected_status", "expected_admitted"),
    [
        (
            RuntimeConcurrencyLimits(tenant_active_limit=1),
            [{"status": "RUNNING", "owner_type": "WORKFLOW", "owner_id": 1, "payload": {"tenantId": "local"}}],
            "tenant",
            "rate_limited",
            False,
        ),
        (
            RuntimeConcurrencyLimits(queue_capacity_limit=1),
            [{"status": "QUEUED", "owner_type": "WORKFLOW", "owner_id": 1, "payload": {"tenantId": "local"}}],
            "queue",
            "rejected",
            False,
        ),
        (
            RuntimeConcurrencyLimits(provider_active_limit=1),
            [
                {
                    "status": "RUNNING",
                    "owner_type": "WORKFLOW",
                    "owner_id": 1,
                    "payload": {"tenantId": "local", "providerKeys": ["llm:1"]},
                }
            ],
            "provider",
            "degraded",
            False,
        ),
        (
            RuntimeConcurrencyLimits(worker_running_limit=1),
            [{"status": "RUNNING", "owner_type": "WORKFLOW", "owner_id": 1, "lease_owner": "worker-a", "payload": {}}],
            "worker",
            "queued",
            True,
        ),
    ],
)
def test_runtime_queue_states_are_explicit_for_limit_outcomes(
    limits: RuntimeConcurrencyLimits,
    rows: list[dict[str, object]],
    expected_level: str,
    expected_status: str,
    expected_admitted: bool,
) -> None:
    decision = RuntimeConcurrencyGate(limits).decide(
        rows,
        owner_type="WORKFLOW",
        owner_id=2,
        tenant_id="local",
        worker_id="worker-a",
        provider_keys=["llm:1"],
    )

    assert decision.level == expected_level
    assert decision.status == expected_status
    assert decision.admitted is expected_admitted
    assert decision.limit == 1
    assert decision.current == 1


def test_runtime_queue_state_defaults_to_queued_when_limits_are_disabled() -> None:
    decision = RuntimeConcurrencyGate(RuntimeConcurrencyLimits()).decide(
        [],
        owner_type="WORKFLOW",
        owner_id=1,
        tenant_id="local",
        provider_keys=[],
    )

    assert decision.level == "none"
    assert decision.status == "queued"
    assert decision.admitted is True
