from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.runtime_job_worker import build_ai_assistant_runtime_job_worker
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository
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
