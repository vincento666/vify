from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.ai_assistant.runtime_job_contract import (
    AI_ASSISTANT_RUNTIME_JOB_TYPE,
    ai_assistant_runtime_job_payload,
)
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository


class AiAssistantRuntimeQueueFull(RuntimeError):
    pass


class AiAssistantRuntimeJobGateway:
    def __init__(
        self,
        session: Session,
        *,
        active_job_limit: int = 100,
    ) -> None:
        self._repository = RuntimeJobRepository(session)
        self._active_job_limit = max(1, int(active_job_limit))

    def enqueue(self, *, run_id: int, session_id: int) -> dict[str, Any]:
        existing = self.get(run_id)
        if existing is not None:
            return existing
        active = self._repository.count_active(owner_types=("AI_ASSISTANT",))
        if active >= self._active_job_limit:
            raise AiAssistantRuntimeQueueFull(
                f"AI Assistant runtime queue is full ({active}/{self._active_job_limit})"
            )
        return self._repository.enqueue(
            run_id=run_id,
            owner_type="AI_ASSISTANT",
            owner_id=session_id,
            job_type=AI_ASSISTANT_RUNTIME_JOB_TYPE,
            payload=ai_assistant_runtime_job_payload(run_id),
        )

    def get(self, run_id: int) -> dict[str, Any] | None:
        return self._repository.get_by_run(
            run_id,
            owner_type="AI_ASSISTANT",
            job_type=AI_ASSISTANT_RUNTIME_JOB_TYPE,
        )

    def cancel(self, run_id: int, *, reason: str) -> dict[str, Any] | None:
        return self._repository.cancel_by_run(
            run_id,
            owner_type="AI_ASSISTANT",
            job_type=AI_ASSISTANT_RUNTIME_JOB_TYPE,
            reason=reason,
        )

    def resume(self, run_id: int) -> dict[str, Any]:
        job = self.get(run_id)
        if job is None:
            raise KeyError(f"AI Assistant runtime job not found: {run_id}")
        if str(job["status"]).upper() == "CANCELLED":
            return self._repository.requeue_cancelled(int(job["id"]))
        return job
