from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.agent.infra.repository import AgentRepository
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.mcp.api.facade import McpFacade
from app.modules.runtime.domain.runtime_job_registry import RuntimeJobHandlerRegistry
from app.modules.runtime.domain.runtime_job_worker import RuntimeJobWorker
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository
from app.modules.runtime.runtime_job_worker import (
    build_registered_runtime_job_worker,
    default_runtime_job_worker_id,
    runtime_job_heartbeat,
)
from app.modules.workflow.domain.runtime_v2 import (
    ChatflowRuntimeV2Service,
    WorkflowRuntimeV2Service,
)
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.api_resource_repository import ApiResourceRepository
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.publish_repository import WorkflowPublishRepository
from app.modules.workflow.infra.realtime.redis_streams import RuntimeEventStreamBus
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.domain.api_resource_service import ApiResourceService
from app.modules.provider.api.facade import ProviderModelFacade


def build_workflow_runtime_job_worker(
    session: Session,
    *,
    worker_id: str | None = None,
    lease_seconds: int = 300,
    event_stream_bus: RuntimeEventStreamBus | None = None,
) -> RuntimeJobWorker:
    return RuntimeJobWorker(
        job_repository=RuntimeJobRepository(session),
        complete_run=lambda run_id: complete_workflow_runtime_job(
            session,
            run_id,
            event_stream_bus=event_stream_bus,
        ),
        complete_job=lambda job: complete_workflow_runtime_job(
            session,
            int(job["run_id"]),
            event_stream_bus=event_stream_bus,
        ),
        worker_id=worker_id or default_runtime_job_worker_id(),
        lease_seconds=lease_seconds,
        owner_types=("WORKFLOW",),
        heartbeat_job=runtime_job_heartbeat(session),
        on_terminal_failure=lambda job, error: fail_runtime_job(
            session,
            int(job["run_id"]),
            job=job,
            error=error,
            event_stream_bus=event_stream_bus,
        ),
    )


def build_chatflow_runtime_job_worker(
    session: Session,
    *,
    worker_id: str | None = None,
    lease_seconds: int = 300,
    event_stream_bus: RuntimeEventStreamBus | None = None,
) -> RuntimeJobWorker:
    return RuntimeJobWorker(
        job_repository=RuntimeJobRepository(session),
        complete_run=lambda run_id: complete_chatflow_runtime_job(
            session,
            run_id,
            event_stream_bus=event_stream_bus,
        ),
        complete_job=lambda job: complete_chatflow_runtime_job(
            session,
            int(job["run_id"]),
            job=job,
            event_stream_bus=event_stream_bus,
        ),
        worker_id=worker_id or default_runtime_job_worker_id("chatflow-runtime-worker"),
        lease_seconds=lease_seconds,
        owner_types=("CHATFLOW",),
        heartbeat_job=runtime_job_heartbeat(session),
        on_terminal_failure=lambda job, error: fail_runtime_job(
            session,
            int(job["run_id"]),
            job=job,
            error=error,
            event_stream_bus=event_stream_bus,
        ),
    )


def build_runtime_job_worker(
    session: Session,
    *,
    owner: str = "workflow",
    worker_id: str | None = None,
    lease_seconds: int = 300,
    event_stream_bus: RuntimeEventStreamBus | None = None,
) -> RuntimeJobWorker:
    normalized_owner = owner.lower()
    if normalized_owner == "workflow":
        return build_workflow_runtime_job_worker(
            session,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
            event_stream_bus=event_stream_bus,
        )
    if normalized_owner == "chatflow":
        return build_chatflow_runtime_job_worker(
            session,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
            event_stream_bus=event_stream_bus,
        )
    if normalized_owner != "both":
        raise ValueError(f"Unsupported runtime job owner: {owner}")
    registry = RuntimeJobHandlerRegistry()
    register_workflow_runtime_job_handlers(
        registry,
        session,
        owner_types=("CHATFLOW", "WORKFLOW"),
        event_stream_bus=event_stream_bus,
    )
    return build_registered_runtime_job_worker(
        session,
        registry=registry,
        worker_id=worker_id or default_runtime_job_worker_id("runtime-worker-both"),
        worker_id_prefix="runtime-worker-both",
        lease_seconds=lease_seconds,
        on_terminal_failure=lambda job, error: fail_runtime_job(
            session,
            int(job["run_id"]),
            job=job,
            error=error,
            event_stream_bus=event_stream_bus,
        ),
    )


def register_workflow_runtime_job_handlers(
    registry: RuntimeJobHandlerRegistry,
    session: Session,
    *,
    owner_types: tuple[str, ...],
    event_stream_bus: RuntimeEventStreamBus | None = None,
) -> None:
    normalized_owners = {owner_type.strip().upper() for owner_type in owner_types}
    if "CHATFLOW" in normalized_owners:
        registry.register(
            "CHATFLOW",
            lambda job: complete_chatflow_runtime_job(
                session,
                int(job["run_id"]),
                job=job,
                event_stream_bus=event_stream_bus,
            ),
        )
    if "WORKFLOW" in normalized_owners:
        registry.register(
            "WORKFLOW",
            lambda job: complete_workflow_runtime_job(
                session,
                int(job["run_id"]),
                event_stream_bus=event_stream_bus,
            ),
        )


def complete_runtime_job(
    session: Session,
    run_id: int,
    *,
    job: dict[str, object] | None = None,
    event_stream_bus: RuntimeEventStreamBus | None = None,
) -> None:
    job = job or RuntimeJobRepository(session).get_by_run(run_id)
    owner_type = str((job or {}).get("owner_type") or "").upper()
    if owner_type == "CHATFLOW":
        complete_chatflow_runtime_job(session, run_id, job=job, event_stream_bus=event_stream_bus)
        return
    if owner_type == "WORKFLOW":
        complete_workflow_runtime_job(session, run_id, event_stream_bus=event_stream_bus)
        return
    raise RuntimeError(f"Unsupported runtime job owner for run {run_id}: {owner_type or '<missing>'}")


def fail_runtime_job(
    session: Session,
    run_id: int,
    *,
    job: dict[str, object] | None = None,
    error: str,
    event_stream_bus: RuntimeEventStreamBus | None = None,
) -> None:
    """Expose terminal resume-job exhaustion to the RuntimeLab stream without consuming its checkpoint."""
    job = job or RuntimeJobRepository(session).get_by_run(run_id)
    if str((job or {}).get("owner_type") or "").upper() != "CHATFLOW" or not _is_runtime_v2_resume_job(job):
        return
    raw_job_id = (job or {}).get("id")
    raw_attempt_count = (job or {}).get("attempt_count")
    if (
        isinstance(raw_job_id, bool)
        or isinstance(raw_attempt_count, bool)
        or not isinstance(raw_job_id, (int, str))
        or not isinstance(raw_attempt_count, (int, str))
    ):
        return
    try:
        job_id = int(raw_job_id)
        attempt_count = int(raw_attempt_count)
    except ValueError:
        return
    current_job = RuntimeJobRepository(session).get(job_id)
    if (
        current_job is None
        or str(current_job.get("status") or "").upper() != "FAILED"
        or int(current_job.get("attempt_count") or 0) != attempt_count
    ):
        return
    raw_checkpoint_id = _runtime_job_payload(job).get("checkpointId")
    if isinstance(raw_checkpoint_id, bool) or not isinstance(raw_checkpoint_id, (int, str)):
        return
    try:
        checkpoint_id = int(raw_checkpoint_id)
    except ValueError:
        return
    ChatflowRuntimeV2Service(
        WorkflowRepository(session),
        ChatflowStateRepository(session, event_stream_bus=event_stream_bus),
    ).record_resume_job_failure(
        run_id,
        checkpoint_id,
        error,
        job_id=job_id,
        attempt_count=attempt_count,
    )


def complete_chatflow_runtime_job(
    session: Session,
    run_id: int,
    *,
    job: dict[str, object] | None = None,
    event_stream_bus: RuntimeEventStreamBus | None = None,
) -> None:
    job = job or RuntimeJobRepository(session).get_by_run(run_id)
    uses_live_llm = _chatflow_job_uses_live_llm(job)
    llm_service = _runtime_v2_llm_service(session, flow_type="CHATFLOW")
    runtime_v2_service = ChatflowRuntimeV2Service(
        WorkflowRepository(session),
        ChatflowStateRepository(session, event_stream_bus=event_stream_bus),
        publish_repository=WorkflowPublishRepository(session),
        knowledge_facade=KnowledgeFacade(session),
        llm_completer_resolver=llm_service.runtime_v2_llm_completer if uses_live_llm else None,
        agent_invoker_resolver=llm_service.runtime_v2_agent_invoker,
        mcp_tool_executor=llm_service.runtime_v2_mcp_tool_executor(),
        api_tool_executor=llm_service.runtime_v2_api_tool_executor(),
    )
    if _is_runtime_v2_resume_job(job):
        payload = _runtime_job_payload(job)
        raw_resume_data = payload.get("resumeData")
        resume_data = dict(raw_resume_data) if isinstance(raw_resume_data, dict) else {}
        raw_checkpoint_id = payload.get("checkpointId")
        checkpoint_id = int(raw_checkpoint_id) if isinstance(raw_checkpoint_id, (int, str)) else None
        runtime_v2_service.resume_run(
            run_id,
            resume_data,
            str(payload.get("idempotencyKey") or "") or None,
            checkpoint_id,
        )
        return
    runtime_v2_service.complete_run(run_id)


def complete_workflow_runtime_job(
    session: Session,
    run_id: int,
    *,
    event_stream_bus: RuntimeEventStreamBus | None = None,
) -> None:
    llm_service = _runtime_v2_llm_service(session, flow_type="WORKFLOW")
    WorkflowRuntimeV2Service(
        WorkflowRepository(session),
        ChatflowStateRepository(session, event_stream_bus=event_stream_bus),
        WorkflowPublishRepository(session),
        knowledge_facade=KnowledgeFacade(session),
        llm_completer_resolver=llm_service.runtime_v2_llm_completer,
        agent_invoker_resolver=llm_service.runtime_v2_agent_invoker,
        mcp_tool_executor=llm_service.runtime_v2_mcp_tool_executor(),
        api_tool_executor=llm_service.runtime_v2_api_tool_executor(),
    ).complete_run(run_id)


def _runtime_v2_llm_service(session: Session, *, flow_type: str) -> WorkflowService:
    return WorkflowService(
        WorkflowRepository(session),
        flow_type=flow_type,
        agent_repository=AgentRepository(session),
        model_facade=ProviderModelFacade(session),
        knowledge_facade=KnowledgeFacade(session),
        mcp_tool_executor=McpFacade(session),
        api_tool_executor=ApiResourceService(ApiResourceRepository(session)),
    )


def _chatflow_job_uses_live_llm(job: dict[str, object] | None) -> bool:
    payload = _runtime_job_payload(job)
    mode = str(payload.get("sopLlmMode") or payload.get("sop_llm_mode") or "live").strip().lower()
    return mode not in {"mock", "fake", "deterministic", "off", "none"}


def _is_runtime_v2_resume_job(job: dict[str, object] | None) -> bool:
    return str((job or {}).get("job_type") or "").startswith("runtime_v2_resume:")


def _runtime_job_payload(job: dict[str, object] | None) -> dict[str, object]:
    payload = job.get("payload") if isinstance(job, dict) else {}
    return payload if isinstance(payload, dict) else {}
