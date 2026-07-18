from datetime import datetime, timedelta

import sqlalchemy as sa

from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.runtime_job_worker import (
    AI_ASSISTANT_RUNTIME_JOB_TYPE,
    build_ai_assistant_runtime_job_worker,
    fail_ai_assistant_runtime_job,
)
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository
from tests.support.mysql import mysql8_session


def test_expired_worker_is_taken_over_and_running_run_resumes_from_checkpoint() -> None:
    with mysql8_session("ai_assistant_standalone_takeover") as session:
        repository = AiAssistantRepository(session)
        service = AiAssistantHarnessService(repository)
        assistant_session = service.create_session(title="Takeover")
        session_id = int(assistant_session["id"])
        started = service.start_message(
            session_id=session_id,
            message="resume after worker crash",
            idempotency_key="standalone-takeover",
        )
        run_id = int(started.run["id"])
        service.queue_started_message(
            session_id=session_id,
            run_id=run_id,
            message="resume after worker crash",
        )
        job_repository = RuntimeJobRepository(session)
        job = job_repository.enqueue(
            run_id=run_id,
            owner_type="AI_ASSISTANT",
            owner_id=session_id,
            job_type=AI_ASSISTANT_RUNTIME_JOB_TYPE,
            payload={"runRef": f"ai-assistant-run:{run_id}"},
        )
        first_claim = job_repository.claim(
            int(job["id"]),
            worker_id="crashed-worker",
            lease_seconds=30,
            owner_types=("AI_ASSISTANT",),
        )
        assert first_claim is not None
        assert repository.claim_run_status(
            run_id,
            expected_status="QUEUED",
            next_status="RUNNING",
            input_payload=dict(service.get_run(run_id)["input_payload"]),
        ) is not None

        runtime_job = sa.Table(
            "runtime_jobs",
            sa.MetaData(),
            autoload_with=session.get_bind(),
        )
        session.execute(
            runtime_job.update()
            .where(runtime_job.c.id == int(job["id"]))
            .values(lease_expires_at=datetime.now() - timedelta(seconds=1))
        )
        session.commit()

        result = build_ai_assistant_runtime_job_worker(
            session,
            worker_id="takeover-worker",
            lease_seconds=30,
        ).run_once(job_id=int(job["id"]))

        assert result["status"] == "COMPLETED"
        assert service.get_run(run_id)["status"] == "COMPLETED"
        event_types = [
            event["type"]
            for event in repository.list_run_events(run_id)
        ]
        assert "run.worker_taken_over" in event_types
        assert event_types.count("run.completed") == 1


def test_terminal_durable_failure_marks_ai_run_failed_without_workflow_adapter() -> None:
    with mysql8_session("ai_assistant_standalone_terminal_failure") as session:
        repository = AiAssistantRepository(session)
        service = AiAssistantHarnessService(repository)
        assistant_session = service.create_session(title="Terminal durable failure")
        session_id = int(assistant_session["id"])
        started = service.start_message(
            session_id=session_id,
            message="fail inconsistent running checkpoint",
            idempotency_key="standalone-terminal-failure",
        )
        run_id = int(started.run["id"])
        service.queue_started_message(
            session_id=session_id,
            run_id=run_id,
            message="fail inconsistent running checkpoint",
        )
        queued = service.get_run(run_id)
        assert queued is not None
        assert repository.claim_run_status(
            run_id,
            expected_status="QUEUED",
            next_status="RUNNING",
            input_payload=dict(queued["input_payload"]),
        ) is not None
        job = RuntimeJobRepository(session).enqueue(
            run_id=run_id,
            owner_type="AI_ASSISTANT",
            owner_id=session_id,
            job_type=AI_ASSISTANT_RUNTIME_JOB_TYPE,
            payload={"runRef": f"ai-assistant-run:{run_id}"},
            max_attempts=1,
        )

        result = build_ai_assistant_runtime_job_worker(
            session,
            worker_id="terminal-failure-worker",
            lease_seconds=30,
        ).run_once(job_id=int(job["id"]))

        assert result["status"] == "FAILED"
        failed_run = service.get_run(run_id)
        assert failed_run is not None
        assert failed_run["status"] == "FAILED"
        response = dict(failed_run["response_payload"])
        assert response["runtimeFailure"] == {
            "runtimeJobId": int(job["id"]),
            "attemptCount": 1,
            "failureClass": "runtime_job_handler_failure",
        }
        events = repository.list_run_events(run_id)
        assert [event["type"] for event in events].count("run.failed") == 1
        assert "not queued or not visible" not in str(events[-1]["payload"])


def test_stale_terminal_callback_cannot_fail_a_requeued_job() -> None:
    with mysql8_session("ai_assistant_stale_terminal_callback") as session:
        repository = AiAssistantRepository(session)
        service = AiAssistantHarnessService(repository)
        assistant_session = service.create_session(title="Stale terminal callback")
        session_id = int(assistant_session["id"])
        started = service.start_message(
            session_id=session_id,
            message="requeue before callback",
            idempotency_key="stale-terminal-callback",
        )
        run_id = int(started.run["id"])
        service.queue_started_message(
            session_id=session_id,
            run_id=run_id,
            message="requeue before callback",
        )
        queued = service.get_run(run_id)
        assert queued is not None
        assert repository.claim_run_status(
            run_id,
            expected_status="QUEUED",
            next_status="RUNNING",
            input_payload=dict(queued["input_payload"]),
        ) is not None
        runtime_jobs = RuntimeJobRepository(session)
        job = runtime_jobs.enqueue(
            run_id=run_id,
            owner_type="AI_ASSISTANT",
            owner_id=session_id,
            job_type=AI_ASSISTANT_RUNTIME_JOB_TYPE,
            payload={"runRef": f"ai-assistant-run:{run_id}"},
            max_attempts=1,
        )
        claimed = runtime_jobs.claim(
            int(job["id"]),
            worker_id="stale-callback-worker",
            lease_seconds=30,
            owner_types=("AI_ASSISTANT",),
        )
        assert claimed is not None
        failed_job = runtime_jobs.fail(
            int(job["id"]),
            worker_id="stale-callback-worker",
            lease_token=str(claimed["lease_token"]),
            error="handler failed",
        )
        assert failed_job["status"] == "FAILED"
        assert runtime_jobs.retry_dlq(int(job["id"]))["status"] == "QUEUED"

        fail_ai_assistant_runtime_job(
            session,
            failed_job,
            error="stale handler failure",
        )

        current_run = service.get_run(run_id)
        assert current_run is not None
        assert current_run["status"] == "RUNNING"
        assert "run.failed" not in {
            event["type"]
            for event in repository.list_run_events(run_id)
        }
