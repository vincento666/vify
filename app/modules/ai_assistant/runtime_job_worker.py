from __future__ import annotations

from collections.abc import Callable
from typing import Any
from hashlib import sha256

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.agent_execution import SubagentExecutionProvider
from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.live_model import create_qwen_live_planner
from app.modules.ai_assistant.domain.permissions import ApprovalPolicy
from app.modules.ai_assistant.domain.tools import ToolRegistry
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

SubagentExecutionProviderFactory = Callable[
    [Session, dict[str, Any]],
    SubagentExecutionProvider,
]


def build_ai_assistant_runtime_job_worker(
    session: Session,
    *,
    worker_id: str | None = None,
    lease_seconds: int = 300,
    child_execution_adapter_factory: SubagentExecutionProviderFactory | None = None,
) -> RuntimeJobWorker:
    registry = RuntimeJobHandlerRegistry()
    register_ai_assistant_runtime_job_handler(
        registry,
        session,
        child_execution_adapter_factory=child_execution_adapter_factory,
    )
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
    *,
    child_execution_adapter_factory: SubagentExecutionProviderFactory | None = None,
) -> None:
    if child_execution_adapter_factory is None:
        registry.register(
            "AI_ASSISTANT",
            lambda job: complete_ai_assistant_runtime_job(session, job),
        )
        return
    registry.register(
        "AI_ASSISTANT",
        lambda job: complete_ai_assistant_runtime_job(
            session,
            job,
            child_execution_adapter_factory=child_execution_adapter_factory,
        ),
    )


def complete_ai_assistant_runtime_job(
    session: Session,
    job: dict[str, Any],
    *,
    child_execution_adapter_factory: SubagentExecutionProviderFactory | None = None,
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
    assistant_repository = AiAssistantRepository(
        session,
        access_scope=access_scope,
        write_guard=lease_guard,
    )
    durable_run = assistant_repository.get_run(run_id)
    if durable_run is None:
        raise RuntimeError(f"AI Assistant run {run_id} is not visible to the claimed job scope")
    principal = _durable_principal(durable_run, access_scope)
    child_execution_adapter = (
        child_execution_adapter_factory(session, principal)
        if child_execution_adapter_factory is not None
        else None
    )
    service = AiAssistantHarnessService(
        assistant_repository,
        live_planner=create_qwen_live_planner(settings),
        approval_policy=ApprovalPolicy(environment=settings.deployment_environment),
        tool_registry=ToolRegistry.with_builtin_tools(
            child_execution_adapter=child_execution_adapter,
        ),
        principal_snapshot=principal,
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


def _durable_principal(
    run: dict[str, Any],
    access_scope: AiAssistantAccessScope,
) -> dict[str, Any]:
    execution_scope = dict((run.get("input_payload") or {}).get("executionScope") or {})
    stored = execution_scope.get("principal")
    stored_principal = dict(stored) if isinstance(stored, dict) else {}
    stored_tenant = str(stored_principal.get("tenantId") or "")
    stored_actor = str(stored_principal.get("actorId") or stored_principal.get("userId") or "")
    if stored_tenant != access_scope.tenant_id or stored_actor != access_scope.user_id:
        stored_principal = {}
    is_local_scope = (
        access_scope.tenant_id == "local"
        and access_scope.user_id == "local-user"
    )
    return {
        "actorId": access_scope.user_id,
        "userId": access_scope.user_id,
        "actorName": str(stored_principal.get("actorName") or access_scope.user_id),
        "tenantId": access_scope.tenant_id,
        "orgId": str(stored_principal.get("orgId") or access_scope.tenant_id),
        "workspaceId": access_scope.workspace_id,
        "requestId": str(stored_principal.get("requestId") or ""),
        "locale": str(stored_principal.get("locale") or "zh-CN"),
        "source": "local" if is_local_scope else "durable-scope",
    }


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
