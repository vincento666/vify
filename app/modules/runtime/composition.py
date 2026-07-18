from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.ai_assistant.runtime_job_worker import (
    fail_ai_assistant_runtime_job,
    register_ai_assistant_runtime_job_handler,
)
from app.modules.runtime.domain.runtime_job_registry import RuntimeJobHandlerRegistry
from app.modules.runtime.domain.runtime_job_worker import RuntimeJobWorker
from app.modules.runtime.runtime_job_worker import build_registered_runtime_job_worker
from app.modules.workflow.infra.realtime.redis_streams import RuntimeEventStreamBus
from app.modules.workflow.runtime_job_worker import (
    fail_runtime_job,
    register_workflow_runtime_job_handlers,
)


def build_runtime_job_worker(
    session: Session,
    *,
    owner: str,
    worker_id: str | None = None,
    lease_seconds: int = 300,
    event_stream_bus: RuntimeEventStreamBus | None = None,
) -> RuntimeJobWorker:
    owner_types = _owner_types(owner)
    registry = RuntimeJobHandlerRegistry()
    register_workflow_runtime_job_handlers(
        registry,
        session,
        owner_types=owner_types,
        event_stream_bus=event_stream_bus,
    )
    if "AI_ASSISTANT" in owner_types:
        register_ai_assistant_runtime_job_handler(registry, session)
    return build_registered_runtime_job_worker(
        session,
        registry=registry,
        worker_id=worker_id,
        worker_id_prefix=f"runtime-worker-{owner.lower()}",
        lease_seconds=lease_seconds,
        on_terminal_failure=lambda job, error: _fail_registered_runtime_job(
            session,
            job,
            error,
            event_stream_bus=event_stream_bus,
        ),
    )


def _fail_registered_runtime_job(
    session: Session,
    job: dict[str, object],
    error: str,
    *,
    event_stream_bus: RuntimeEventStreamBus | None,
) -> None:
    if str(job.get("owner_type") or "").upper() == "AI_ASSISTANT":
        fail_ai_assistant_runtime_job(session, job, error=error)
        return
    fail_runtime_job(
        session,
        int(job["run_id"]),
        job=job,
        error=error,
        event_stream_bus=event_stream_bus,
    )


def _owner_types(owner: str) -> tuple[str, ...]:
    normalized_owner = owner.strip().lower()
    selections = {
        "workflow": ("WORKFLOW",),
        "chatflow": ("CHATFLOW",),
        "ai-assistant": ("AI_ASSISTANT",),
        "both": ("CHATFLOW", "WORKFLOW"),
        "all": ("AI_ASSISTANT", "CHATFLOW", "WORKFLOW"),
    }
    try:
        return selections[normalized_owner]
    except KeyError as exc:
        raise ValueError(f"Unsupported runtime job owner: {owner}") from exc
