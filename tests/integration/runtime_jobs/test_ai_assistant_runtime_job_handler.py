from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.tools import ToolRegistry
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.runtime_job_worker import build_ai_assistant_runtime_job_worker
from app.modules.customer_assistant.harness_adapter import (
    CustomerAssistantExecutionAdapter,
    create_customer_assistant_execution_adapter,
)
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository
from app.core.host.context import RequestContext
from tests.support.mysql import mysql8_session


def test_ai_assistant_runtime_job_handler_completes_queued_run() -> None:
    with mysql8_session("runtime_jobs_ai_assistant_handler") as session:
        service = AiAssistantHarnessService(AiAssistantRepository(session))
        assistant_session = service.create_session(title="standalone runtime handler")
        session_id = int(assistant_session["id"])
        started = service.start_message(
            session_id=session_id,
            message="execute through standalone runtime handler",
            idempotency_key="runtime-handler-1",
        )
        run_id = int(started.run["id"])
        service.queue_started_message(
            session_id=session_id,
            run_id=run_id,
            message="execute through standalone runtime handler",
        )
        job = RuntimeJobRepository(session).enqueue(
            run_id=run_id,
            owner_type="AI_ASSISTANT",
            owner_id=session_id,
            job_type="ai_assistant_run",
        )

        result = build_ai_assistant_runtime_job_worker(
            session,
            worker_id="ai-assistant-test-worker",
        ).run_once(job_id=int(job["id"]))

        assert result["status"] == "COMPLETED"
        assert service.get_run(run_id)["status"] == "COMPLETED"


def test_ai_assistant_runtime_job_handler_restores_scope_from_durable_run() -> None:
    with mysql8_session("runtime_jobs_ai_assistant_scoped_handler") as session:
        scope = AiAssistantAccessScope(
            tenant_id="scoped-worker-tenant",
            user_id="scoped-worker-user",
            workspace_id="scoped-worker-workspace",
        )
        service = AiAssistantHarnessService(
            AiAssistantRepository(session, access_scope=scope)
        )
        assistant_session = service.create_session(title="scoped standalone handler")
        session_id = int(assistant_session["id"])
        started = service.start_message(
            session_id=session_id,
            message="restore trusted scope from durable run",
            idempotency_key="runtime-handler-scoped-1",
        )
        run_id = int(started.run["id"])
        service.queue_started_message(
            session_id=session_id,
            run_id=run_id,
            message="restore trusted scope from durable run",
        )
        job = RuntimeJobRepository(session).enqueue(
            run_id=run_id,
            owner_type="AI_ASSISTANT",
            owner_id=session_id,
            job_type="ai_assistant_run",
            payload={"runId": run_id},
        )

        result = build_ai_assistant_runtime_job_worker(
            session,
            worker_id="ai-assistant-scoped-worker",
        ).run_once(job_id=int(job["id"]))

        assert result["status"] == "COMPLETED"
        assert service.get_run(run_id)["status"] == "COMPLETED"
        execution_scope = service.get_run(run_id)["input_payload"]["executionScope"]
        assert execution_scope == {
            "schemaVersion": "ai-assistant.scope/1",
            "tenantId": "scoped-worker-tenant",
            "userId": "scoped-worker-user",
            "workspaceId": "scoped-worker-workspace",
            "principal": {
                "actorId": "scoped-worker-user",
                "tenantId": "scoped-worker-tenant",
                "source": "durable-scope",
            },
            "permissionPolicyRef": "ai-assistant-host-policy/v1",
        }
        assert job["payload"] == {"runId": run_id}


def test_ai_assistant_runtime_job_handler_uses_composed_subagent_adapter() -> None:
    with mysql8_session("runtime_jobs_ai_assistant_subagent_adapter") as session:
        owner = RequestContext(
            actor_id="durable-child-owner",
            actor_name="Durable Child Owner",
            tenant_id="tenant-child",
            org_id="org-child",
            source="test",
        )
        customer_repository = CustomerAssistantRepository(session)
        customer_session = customer_repository.create_session(
            {"hostContext": owner.audit_metadata()}
        )
        customer_run, _ = customer_repository.create_run(
            int(customer_session["id"]),
            idempotency_key="durable-child",
            request_hash="child-hash",
            input_payload={"message": "查询客服子任务"},
        )
        service = AiAssistantHarnessService(
            AiAssistantRepository(
                session,
                access_scope=AiAssistantAccessScope(
                    tenant_id=owner.tenant_id,
                    user_id=owner.actor_id,
                    workspace_id="workspace-child",
                ),
            ),
            tool_registry=ToolRegistry.with_builtin_tools(
                child_execution_adapter=CustomerAssistantExecutionAdapter(
                    customer_repository,
                    owner,
                ),
            ),
            principal_snapshot=owner.audit_metadata(),
        )
        assistant_session = service.create_session(title="durable subagent adapter")
        session_id = int(assistant_session["id"])
        tool_input = {
            "sessionId": int(customer_session["id"]),
            "runId": int(customer_run["id"]),
        }
        started = service.start_message(
            session_id=session_id,
            message="检查客服子任务",
            idempotency_key="runtime-handler-child-1",
            tool_name="customer_assistant_subagent_bridge",
            tool_input=tool_input,
        )
        run_id = int(started.run["id"])
        service.queue_started_message(
            session_id=session_id,
            run_id=run_id,
            message="检查客服子任务",
            tool_name="customer_assistant_subagent_bridge",
            tool_input=tool_input,
        )
        job = RuntimeJobRepository(session).enqueue(
            run_id=run_id,
            owner_type="AI_ASSISTANT",
            owner_id=session_id,
            job_type="ai_assistant_run",
        )

        result = build_ai_assistant_runtime_job_worker(
            session,
            worker_id="ai-assistant-subagent-worker",
            child_execution_adapter_factory=create_customer_assistant_execution_adapter,
        ).run_once(job_id=int(job["id"]))

        assert result["status"] == "COMPLETED"
        events = service.list_run_events(run_id)
        subagent_events = [
            event
            for event in events
            if event["type"] == "subagent.execution_started"
        ]
        assert subagent_events, [
            (
                event["type"],
                event["status"],
                event["payload"],
            )
            for event in events
            if str(event["type"]).startswith(("tool.", "subagent."))
        ]
        assert subagent_events[0]["payload"]["parentExecutionId"] == f"ai-assistant-run-{run_id}"
        assert subagent_events[0]["correlation_ids"]["parentActivityId"].startswith("tool:")


def test_ai_assistant_runtime_job_handler_rejects_mismatched_job_owner() -> None:
    with mysql8_session("runtime_jobs_ai_assistant_wrong_owner") as session:
        service = AiAssistantHarnessService(AiAssistantRepository(session))
        assistant_session = service.create_session(title="wrong owner")
        session_id = int(assistant_session["id"])
        started = service.start_message(
            session_id=session_id,
            message="must not run under another owner",
            idempotency_key="runtime-handler-wrong-owner",
        )
        run_id = int(started.run["id"])
        service.queue_started_message(
            session_id=session_id,
            run_id=run_id,
            message="must not run under another owner",
        )
        job = RuntimeJobRepository(session).enqueue(
            run_id=run_id,
            owner_type="AI_ASSISTANT",
            owner_id=session_id + 1,
            job_type="ai_assistant_run",
            payload={"runId": run_id},
        )

        result = build_ai_assistant_runtime_job_worker(
            session,
            worker_id="ai-assistant-wrong-owner-worker",
        ).run_once(job_id=int(job["id"]))
        stored = RuntimeJobRepository(session).get(int(job["id"]))

        assert result["status"] == "QUEUED"
        assert stored is not None
        assert "does not match the claimed job scope" in str(stored["last_error"])
        assert service.get_run(run_id)["status"] == "QUEUED"
