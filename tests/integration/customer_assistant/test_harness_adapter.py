from contextlib import contextmanager
from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.core.errors import BizError
from app.core.host.context import RequestContext
from app.modules.agent_execution import AgentExecutionStatus
from app.modules.customer_assistant.harness_adapter import CustomerAssistantExecutionAdapter
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)
from tests.support.mysql import mysql8_session


def test_adapter_resolves_persisted_running_and_completed_lifecycle() -> None:
    owner = RequestContext(
        actor_id="operator-a",
        tenant_id="tenant-a",
        org_id="org-a",
        request_id="request-a",
        source="test",
    )
    with _session() as session:
        repository = CustomerAssistantRepository(session)
        assistant_session = repository.create_session({"hostContext": owner.audit_metadata()})
        run, _ = repository.create_run(
            int(assistant_session["id"]),
            idempotency_key="adapter-running",
            request_hash="hash",
            input_payload={"message": "查询订单"},
        )
        repository.append_event(
            int(assistant_session["id"]),
            "sub_agent_progress",
            {"summary": "正在检索订单"},
            run_id=int(run["id"]),
            source="customer_assistant_subagent",
        )
        adapter = CustomerAssistantExecutionAdapter(repository, owner)

        running = adapter.attach(
            parent_execution_id="ai-assistant-run-9",
            session_id=int(assistant_session["id"]),
            run_id=int(run["id"]),
        )

        assert running.status is AgentExecutionStatus.RUNNING
        assert running.parent_execution_id == "ai-assistant-run-9"
        assert running.current_summary == "正在检索订单"
        assert running.status_ref.endswith(f"/runs/{run['id']}")
        assert running.scope == {"tenantId": "tenant-a", "orgId": "org-a"}
        assert running.audit["requestId"] == "request-a"

        repository.complete_run(
            int(run["id"]),
            response_payload={"customerReplyDraft": "订单已找到"},
        )
        completed = adapter.observe(execution_id=running.execution_id)

        assert completed.status is AgentExecutionStatus.COMPLETED
        assert completed.completed_at is not None


def test_adapter_rejects_cross_tenant_reference() -> None:
    owner = RequestContext(tenant_id="tenant-a", org_id="org-a", source="test")
    other = RequestContext(tenant_id="tenant-b", org_id="org-b", source="test")
    with _session() as session:
        repository = CustomerAssistantRepository(session)
        assistant_session = repository.create_session({"hostContext": owner.audit_metadata()})
        run, _ = repository.create_run(
            int(assistant_session["id"]),
            idempotency_key="adapter-scope",
            request_hash="hash",
            input_payload={"message": "查询订单"},
        )

        with pytest.raises(BizError):
            CustomerAssistantExecutionAdapter(repository, other).attach(
                parent_execution_id="ai-assistant-run-9",
                session_id=int(assistant_session["id"]),
                run_id=int(run["id"]),
            )


def test_adapter_rejects_cross_org_reference_within_tenant() -> None:
    owner = RequestContext(tenant_id="tenant-a", org_id="org-a", source="test")
    other_org = RequestContext(tenant_id="tenant-a", org_id="org-b", source="test")
    with _session() as session:
        repository = CustomerAssistantRepository(session)
        assistant_session = repository.create_session({"hostContext": owner.audit_metadata()})
        run, _ = repository.create_run(
            int(assistant_session["id"]),
            idempotency_key="adapter-org-scope",
            request_hash="hash",
            input_payload={"message": "查询订单"},
        )

        with pytest.raises(BizError):
            CustomerAssistantExecutionAdapter(repository, other_org).attach(
                parent_execution_id="ai-assistant-run-9",
                session_id=int(assistant_session["id"]),
                run_id=int(run["id"]),
            )


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session(
        "customer_assistant_harness_adapter",
        tables=customer_assistant_tables(),
        register=register_customer_assistant_tables,
    ) as session:
        yield session
