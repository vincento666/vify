from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class RuntimeJobRepositoryProtocol(Protocol):
    def claim_next(self, *, worker_id: str, lease_seconds: int = 30) -> dict[str, Any] | None: ...

    def claim(self, job_id: int, *, worker_id: str, lease_seconds: int = 30) -> dict[str, Any] | None: ...

    def complete(self, job_id: int, *, worker_id: str, lease_token: str | None = None) -> dict[str, Any]: ...

    def fail(
        self,
        job_id: int,
        *,
        worker_id: str,
        error: str,
        lease_token: str | None = None,
    ) -> dict[str, Any]: ...


class RuntimeJobWorker:
    def __init__(
        self,
        *,
        job_repository: RuntimeJobRepositoryProtocol,
        complete_run: Callable[[int], None],
        worker_id: str,
        lease_seconds: int = 300,
    ) -> None:
        self._job_repository = job_repository
        self._complete_run = complete_run
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds

    def run_once(self, job_id: int | None = None) -> dict[str, Any]:
        job = (
            self._job_repository.claim(job_id, worker_id=self._worker_id, lease_seconds=self._lease_seconds)
            if job_id is not None
            else self._job_repository.claim_next(worker_id=self._worker_id, lease_seconds=self._lease_seconds)
        )
        if job is None:
            return {"claimed": False, "status": "IDLE"}
        claimed_job_id = int(job["id"])
        lease_token = str(job.get("lease_token") or "")
        try:
            self._complete_run(int(job["run_id"]))
        except Exception as exc:
            failed = self._job_repository.fail(
                claimed_job_id,
                worker_id=self._worker_id,
                lease_token=lease_token,
                error=str(exc),
            )
            return {
                "claimed": True,
                "jobId": claimed_job_id,
                "runId": int(job["run_id"]),
                "status": failed["status"],
                "error": str(exc),
            }
        completed = self._job_repository.complete(
            claimed_job_id,
            worker_id=self._worker_id,
            lease_token=lease_token,
        )
        return {
            "claimed": True,
            "jobId": claimed_job_id,
            "runId": int(job["run_id"]),
            "status": completed["status"],
        }
