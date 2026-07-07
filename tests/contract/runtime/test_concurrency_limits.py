from __future__ import annotations

from app.modules.runtime.domain.concurrency_limits import RuntimeConcurrencyGate, RuntimeConcurrencyLimits


def test_runtime_concurrency_gate_counts_tenant_owner_worker_and_provider_levels() -> None:
    rows = [
        _job("QUEUED", "WORKFLOW", 10, tenant_id="tenant-a", provider_keys=["llm:1"]),
        _job("RUNNING", "WORKFLOW", 10, tenant_id="tenant-a", provider_keys=["llm:2"], lease_owner="worker-a"),
        _job("RUNNING", "CHATFLOW", 20, tenant_id="tenant-b", provider_keys=["llm:1"], lease_owner="worker-b"),
    ]
    gate = RuntimeConcurrencyGate(
        RuntimeConcurrencyLimits(
            tenant_active_limit=10,
            workflow_active_limit=5,
            chatflow_active_limit=5,
            worker_running_limit=5,
            provider_active_limit=5,
        )
    )

    snapshot = gate.snapshot(
        rows,
        owner_type="WORKFLOW",
        owner_id=10,
        tenant_id="tenant-a",
        worker_id="worker-a",
        provider_keys=["llm:1"],
    )

    assert snapshot.tenant_active == 2
    assert snapshot.owner_active == 2
    assert snapshot.worker_running == 1
    assert snapshot.provider_active == 2


def test_runtime_concurrency_gate_uses_specific_workflow_and_chatflow_limits() -> None:
    workflow_gate = RuntimeConcurrencyGate(RuntimeConcurrencyLimits(workflow_active_limit=1))
    chatflow_gate = RuntimeConcurrencyGate(RuntimeConcurrencyLimits(chatflow_active_limit=1))

    workflow_decision = workflow_gate.decide(
        [_job("RUNNING", "WORKFLOW", 10)],
        owner_type="WORKFLOW",
        owner_id=10,
        tenant_id="local",
        provider_keys=[],
    )
    chatflow_decision = chatflow_gate.decide(
        [_job("RUNNING", "CHATFLOW", 20)],
        owner_type="CHATFLOW",
        owner_id=20,
        tenant_id="local",
        provider_keys=[],
    )

    assert workflow_decision.level == "workflow"
    assert workflow_decision.status == "queued"
    assert workflow_decision.admitted is True
    assert chatflow_decision.level == "chatflow"
    assert chatflow_decision.status == "queued"
    assert chatflow_decision.admitted is True


def _job(
    status: str,
    owner_type: str,
    owner_id: int,
    *,
    tenant_id: str = "local",
    provider_keys: list[str] | None = None,
    lease_owner: str = "",
) -> dict[str, object]:
    return {
        "status": status,
        "owner_type": owner_type,
        "owner_id": owner_id,
        "lease_owner": lease_owner,
        "payload": {"tenantId": tenant_id, "providerKeys": provider_keys or []},
    }
