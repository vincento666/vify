from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.live_model import create_qwen_live_planner
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.runtime.domain.runtime_job_registry import RuntimeJobHandlerRegistry
from app.modules.runtime.domain.runtime_job_worker import RuntimeJobWorker
from app.modules.runtime.runtime_job_worker import build_registered_runtime_job_worker


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
    )


def register_ai_assistant_runtime_job_handler(
    registry: RuntimeJobHandlerRegistry,
    session: Session,
) -> None:
    registry.register(
        "AI_ASSISTANT",
        lambda job: complete_ai_assistant_runtime_job(session, int(job["run_id"])),
    )


def complete_ai_assistant_runtime_job(session: Session, run_id: int) -> None:
    service = AiAssistantHarnessService(
        AiAssistantRepository(session),
        live_planner=create_qwen_live_planner(get_settings()),
    )
    result = service.process_queued_run(run_id)
    if result is None:
        raise RuntimeError(f"AI Assistant run {run_id} is not queued or not visible to this worker")
