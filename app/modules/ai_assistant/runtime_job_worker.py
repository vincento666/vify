from __future__ import annotations

from typing import Any
from hashlib import sha256

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.live_model import create_qwen_live_planner
from app.modules.ai_assistant.domain.permissions import ApprovalPolicy
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.infra.runtime_job_lease import RuntimeJobLeaseGuard
from app.modules.ai_assistant.runtime_job_contract import AI_ASSISTANT_RUNTIME_JOB_TYPE
from app.modules.runtime.domain.runtime_job_registry import RuntimeJobHandlerRegistry
from app.modules.runtime.domain.runtime_job_worker import RuntimeJobWorker
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository
from app.modules.runtime.runtime_job_worker import build_registered_runtime_job_worker


__all__ = [
    "AI_ASSISTANT_RUNTIME_JOB_TYPE",
    "build_ai_assistant_runtime_job_worker",
    "complete_ai_assistant_runtime_job",
    "fail_ai_assistant_runtime_job",
    "register_ai_assistant_runtime_job_handler",
]


def build_ai_assistant_runtime_job_worker(
    session: Session,
    *,
    worker_id: str | None = None,
    lease_seconds: int = 300,
) -> RuntimeJobWorker:
    registry = RuntimeJobHandlerRegistry()
    register_ai_assistant_runtime_job_handler(registry, session)
    return build_registered_runtime_job_worker(
        session,
        registry=registry,
        worker_id=worker_id,
        worker_id_prefix="ai-assistant-runtime-worker",
        lease_seconds=lease_seconds,
        on_terminal_failure=lambda job, error: fail_ai_assistant_runtime_job(
            session,
            job,
            error=error,
        ),
    )


def register_ai_assistant_runtime_job_handler(
    registry: RuntimeJobHandlerRegistry,
    session: Session,
) -> None:
    registry.register(
        "AI_ASSISTANT",
        lambda job: complete_ai_assistant_runtime_job(session, job),
    )


def complete_ai_assistant_runtime_job(
    session: Session,
    job: dict[str, Any],
) -> None:
    run_id = int(job["run_id"])
    access_scope = AiAssistantRepository.access_scope_for_durable_run(
        session,
        run_id,
        expected_session_id=int(job["owner_id"]),
    )
    if access_scope is None:
        raise RuntimeError(f"AI Assistant run {run_id} does not match the claimed job scope")
    lease_fence = str(job.get("lease_token") or "")
    worker_id = str(job.get("lease_owner") or "")
    if not lease_fence or not worker_id:
        raise RuntimeError(f"AI Assistant runtime job {job['id']} has no active lease")
    settings = get_settings()
    lease_guard = RuntimeJobLeaseGuard(
        session,
        job_id=int(job["id"]),
        worker_id=worker_id,
        lease_fence=lease_fence,
    )
    service = AiAssistantHarnessService(
        AiAssistantRepository(
            session,
            access_scope=access_scope,
            write_guard=lease_guard,
        ),
        live_planner=create_qwen_live_planner(settings),
        approval_policy=ApprovalPolicy(environment=settings.deployment_environment),
    )
    result = service.process_queued_run(
        run_id,
        worker_claim={
            "scope": "durable-runtime-job",
            "runtimeJobId": int(job["id"]),
            "workerId": worker_id,
            "attempt": int(job.get("attempt_count") or 1),
            "leaseFenceHash": sha256(lease_fence.encode()).hexdigest()[:16],
        },
        allow_takeover=int(job.get("attempt_count") or 1) > 1,
    )
    if result is None:
        raise RuntimeError(f"AI Assistant run {run_id} is not queued or not visible to this worker")


def fail_ai_assistant_runtime_job(
    session: Session,
    job: dict[str, Any],
    *,
    error: str,
) -> None:
    """Expose exhausted durable execution without crossing into Workflow state."""
    current_job = RuntimeJobRepository(session).get(int(job["id"]))
    if (
        current_job is None
        or str(current_job.get("status") or "").upper() != "FAILED"
        or int(current_job.get("attempt_count") or 0)
        != int(job.get("attempt_count") or 0)
    ):
        return
    run_id = int(job["run_id"])
    session_id = int(job["owner_id"])
    access_scope = AiAssistantRepository.access_scope_for_durable_run(
        session,
        run_id,
        expected_session_id=session_id,
    )
    if access_scope is None:
        return
    repository = AiAssistantRepository(session, access_scope=access_scope)
    run = repository.get_run(run_id)
    if run is None or str(run["status"]).upper() in {
        "CANCELLED",
        "COMPLETED",
        "DENIED",
        "FAILED",
    }:
        return
    public_reason = "AI Assistant durable worker exhausted its retry budget."
    response = dict(run.get("response_payload") or {})
    response.update(
        {
            "finalAnswer": public_reason,
            "runtimeFailure": {
                "runtimeJobId": int(job["id"]),
                "attemptCount": int(job.get("attempt_count") or 0),
                "failureClass": "runtime_job_handler_failure",
            },
        }
    )
    repository.complete_run(run_id, response, status="FAILED")
    repository.append_event(
        run_id=run_id,
        session_id=session_id,
        event_type="run.failed",
        visible_title="运行失败",
        visible_summary=public_reason,
        payload=response["runtimeFailure"],
        status="FAILED",
        level="error",
    )
