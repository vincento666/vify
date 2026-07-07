from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class RuntimeJobRepositoryProtocol(Protocol):
    def get(self, job_id: int) -> dict[str, Any] | None: ...

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: int = 30,
        owner_types: tuple[str, ...] | None = None,
    ) -> dict[str, Any] | None: ...

    def claim(
        self,
        job_id: int,
        *,
        worker_id: str,
        lease_seconds: int = 30,
        owner_types: tuple[str, ...] | None = None,
    ) -> dict[str, Any] | None: ...

    def complete(self, job_id: int, *, worker_id: str, lease_token: str | None = None) -> dict[str, Any]: ...

    def fail(
        self,
        job_id: int,
        *,
        worker_id: str,
        error: str,
        lease_token: str | None = None,
        retry_backoff_seconds: tuple[int, ...] = (5, 30, 120),
    ) -> dict[str, Any]: ...


class RuntimeJobWorker:
    def __init__(
        self,
        *,
        job_repository: RuntimeJobRepositoryProtocol,
        complete_run: Callable[[int], None],
        worker_id: str,
        lease_seconds: int = 300,
        owner_types: tuple[str, ...] | None = None,
    ) -> None:
        self._job_repository = job_repository
        self._complete_run = complete_run
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds
        self._owner_types = _normalize_owner_types(owner_types)

    def run_once(self, job_id: int | None = None) -> dict[str, Any]:
        job = (
            self._job_repository.claim(
                job_id,
                worker_id=self._worker_id,
                lease_seconds=self._lease_seconds,
                owner_types=self._owner_types,
            )
            if job_id is not None
            else self._job_repository.claim_next(
                worker_id=self._worker_id,
                lease_seconds=self._lease_seconds,
                owner_types=self._owner_types,
            )
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
        try:
            completed = self._job_repository.complete(
                claimed_job_id,
                worker_id=self._worker_id,
                lease_token=lease_token,
            )
        except RuntimeError:
            current = self._job_repository.get(claimed_job_id)
            if current is not None and str(current.get("status") or "").upper() in {"CANCELLED", "IGNORED"}:
                return {
                    "claimed": True,
                    "jobId": claimed_job_id,
                    "runId": int(job["run_id"]),
                    "status": str(current["status"]),
                }
            raise
        return {
            "claimed": True,
            "jobId": claimed_job_id,
            "runId": int(job["run_id"]),
            "status": completed["status"],
        }


def _normalize_owner_types(owner_types: tuple[str, ...] | None) -> tuple[str, ...] | None:
    if owner_types is None:
        return None
    normalized = tuple(sorted({str(owner_type).upper() for owner_type in owner_types if str(owner_type).strip()}))
    return normalized or None
