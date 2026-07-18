from __future__ import annotations

from collections.abc import Callable
import threading
from typing import Any, Protocol


class RuntimeJobLeaseLost(RuntimeError):
    pass


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

    def heartbeat(
        self,
        job_id: int,
        *,
        worker_id: str,
        lease_seconds: int = 30,
        lease_token: str | None = None,
    ) -> dict[str, Any]: ...


class RuntimeJobWorker:
    def __init__(
        self,
        *,
        job_repository: RuntimeJobRepositoryProtocol,
        complete_run: Callable[[int], None] | None = None,
        complete_job: Callable[[dict[str, Any]], None] | None = None,
        worker_id: str,
        lease_seconds: int = 300,
        owner_types: tuple[str, ...] | None = None,
        heartbeat_job: Callable[[int, str, str, int], None] | None = None,
        on_terminal_failure: Callable[[dict[str, Any], str], None] | None = None,
    ) -> None:
        if complete_run is None and complete_job is None:
            raise ValueError("RuntimeJobWorker requires a run or job handler")
        self._job_repository = job_repository
        self._complete_run = complete_run
        self._complete_job = complete_job
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds
        self._owner_types = _normalize_owner_types(owner_types)
        self._heartbeat_job = heartbeat_job
        self._on_terminal_failure = on_terminal_failure

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
        stop_heartbeat = threading.Event()
        heartbeat_thread: threading.Thread | None = None
        if self._heartbeat_job is not None:
            heartbeat_thread = threading.Thread(
                target=self._renew_lease_until_complete,
                args=(stop_heartbeat, claimed_job_id, lease_token),
                daemon=True,
                name=f"runtime-job-heartbeat-{claimed_job_id}",
            )
            heartbeat_thread.start()
        try:
            if self._complete_job is not None:
                self._complete_job(job)
            else:
                assert self._complete_run is not None
                self._complete_run(int(job["run_id"]))
        except Exception as exc:
            try:
                failed = self._job_repository.fail(
                    claimed_job_id,
                    worker_id=self._worker_id,
                    lease_token=lease_token,
                    error=str(exc),
                )
            except RuntimeJobLeaseLost:
                current = self._job_repository.get(claimed_job_id)
                return {
                    "claimed": True,
                    "jobId": claimed_job_id,
                    "runId": int(job["run_id"]),
                    "status": "LEASE_LOST",
                    "jobStatus": (
                        str(current.get("status") or "")
                        if current is not None
                        else "MISSING"
                    ),
                    "error": str(exc),
                }
            if str(failed.get("status") or "").upper() == "FAILED" and self._on_terminal_failure is not None:
                self._on_terminal_failure(failed, str(exc))
            return {
                "claimed": True,
                "jobId": claimed_job_id,
                "runId": int(job["run_id"]),
                "status": failed["status"],
                "error": str(exc),
            }
        finally:
            stop_heartbeat.set()
            if heartbeat_thread is not None:
                heartbeat_thread.join(timeout=1)
        try:
            completed = self._job_repository.complete(
                claimed_job_id,
                worker_id=self._worker_id,
                lease_token=lease_token,
            )
        except RuntimeError as exc:
            current = self._job_repository.get(claimed_job_id)
            if current is not None and str(current.get("status") or "").upper() in {"CANCELLED", "IGNORED"}:
                return {
                    "claimed": True,
                    "jobId": claimed_job_id,
                    "runId": int(job["run_id"]),
                    "status": str(current["status"]),
                }
            if not isinstance(exc, RuntimeJobLeaseLost):
                raise
            return {
                "claimed": True,
                "jobId": claimed_job_id,
                "runId": int(job["run_id"]),
                "status": "LEASE_LOST",
                "jobStatus": (
                    str(current.get("status") or "")
                    if current is not None
                    else "MISSING"
                ),
            }
        return {
            "claimed": True,
            "jobId": claimed_job_id,
            "runId": int(job["run_id"]),
            "status": completed["status"],
        }

    def _renew_lease_until_complete(self, stop: threading.Event, job_id: int, lease_token: str) -> None:
        interval_seconds = max(0.05, min(30.0, float(self._lease_seconds) / 3))
        while not stop.wait(interval_seconds):
            try:
                assert self._heartbeat_job is not None
                self._heartbeat_job(job_id, self._worker_id, lease_token, self._lease_seconds)
            except Exception:
                return


def _normalize_owner_types(owner_types: tuple[str, ...] | None) -> tuple[str, ...] | None:
    if owner_types is None:
        return None
    normalized = tuple(sorted({str(owner_type).upper() for owner_type in owner_types if str(owner_type).strip()}))
    return normalized or None
