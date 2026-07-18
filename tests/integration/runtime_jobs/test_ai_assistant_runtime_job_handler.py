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
