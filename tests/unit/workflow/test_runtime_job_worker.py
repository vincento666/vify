import unittest
from threading import Event

from app.modules.runtime.domain.runtime_job_worker import RuntimeJobWorker


class RuntimeJobWorkerTest(unittest.TestCase):
    def test_run_once_claims_and_completes_one_job(self) -> None:
        repository = _FakeJobRepository(
            {
                "id": 7,
                "run_id": 11,
                "status": "QUEUED",
                "lease_owner": "",
            }
        )
        completed_runs: list[int] = []
        worker = RuntimeJobWorker(
            job_repository=repository,
            complete_run=lambda run_id: completed_runs.append(run_id),
            worker_id="worker-a",
        )

        result = worker.run_once()

        self.assertTrue(result["claimed"])
        self.assertEqual(result["jobId"], 7)
        self.assertEqual(completed_runs, [11])
        self.assertEqual(repository.completed_job_id, 7)

    def test_run_once_marks_job_failed_when_completion_raises(self) -> None:
        repository = _FakeJobRepository({"id": 8, "run_id": 12, "status": "QUEUED"})

        def fail(_run_id: int) -> None:
            raise RuntimeError("worker boom")

        worker = RuntimeJobWorker(job_repository=repository, complete_run=fail, worker_id="worker-a")

        result = worker.run_once()

        self.assertTrue(result["claimed"])
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(repository.failed_error, "worker boom")

    def test_run_once_projects_terminal_failure_after_retry_budget_is_exhausted(self) -> None:
        repository = _FakeJobRepository({"id": 81, "run_id": 121, "status": "QUEUED"})
        projected: list[tuple[int, str]] = []

        def fail(_run_id: int) -> None:
            raise RuntimeError("provider unavailable")

        worker = RuntimeJobWorker(
            job_repository=repository,
            complete_run=fail,
            worker_id="worker-a",
            on_terminal_failure=lambda job, error: projected.append((int(job["run_id"]), error)),
        )

        result = worker.run_once()

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(projected, [(121, "provider unavailable")])

    def test_run_once_reports_idle_when_no_job_is_claimed(self) -> None:
        repository = _FakeJobRepository(None)
        worker = RuntimeJobWorker(job_repository=repository, complete_run=lambda _run_id: None, worker_id="worker-a")

        result = worker.run_once()

        self.assertFalse(result["claimed"])
        self.assertEqual(result["status"], "IDLE")

    def test_run_once_passes_owner_filter_to_repository_claims(self) -> None:
        repository = _FakeJobRepository({"id": 9, "run_id": 13, "status": "QUEUED"})
        worker = RuntimeJobWorker(
            job_repository=repository,
            complete_run=lambda _run_id: None,
            worker_id="chatflow-worker",
            owner_types=("CHATFLOW",),
        )

        worker.run_once()
        worker.run_once(job_id=9)

        self.assertEqual(repository.claim_next_owner_types, ("CHATFLOW",))
        self.assertEqual(repository.claim_owner_types, ("CHATFLOW",))

    def test_run_once_returns_cancelled_when_job_cancelled_before_complete(self) -> None:
        repository = _FakeJobRepository({"id": 10, "run_id": 14, "status": "QUEUED"})
        repository.complete_error = RuntimeError("lease no longer owned")
        repository.current_job = {"id": 10, "run_id": 14, "status": "CANCELLED"}
        worker = RuntimeJobWorker(
            job_repository=repository,
            complete_run=lambda _run_id: None,
            worker_id="worker-a",
        )

        result = worker.run_once()

        self.assertTrue(result["claimed"])
        self.assertEqual(result["jobId"], 10)
        self.assertEqual(result["runId"], 14)
        self.assertEqual(result["status"], "CANCELLED")

    def test_run_once_renews_lease_while_completion_is_running(self) -> None:
        repository = _FakeJobRepository({"id": 11, "run_id": 15, "status": "QUEUED", "lease_token": "lease-11"})
        heartbeat_seen = Event()
        heartbeats: list[tuple[int, str, str, int]] = []

        def heartbeat(job_id: int, worker_id: str, lease_token: str, lease_seconds: int) -> None:
            heartbeats.append((job_id, worker_id, lease_token, lease_seconds))
            heartbeat_seen.set()

        def complete(_run_id: int) -> None:
            self.assertTrue(heartbeat_seen.wait(timeout=0.5))

        worker = RuntimeJobWorker(
            job_repository=repository,
            complete_run=complete,
            worker_id="worker-a",
            lease_seconds=1,
            heartbeat_job=heartbeat,
        )

        result = worker.run_once()

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(heartbeats, [(11, "worker-a", "lease-11", 1)])


class _FakeJobRepository:
    def __init__(self, job: dict[str, object] | None) -> None:
        self._job = job
        self.current_job: dict[str, object] | None = None
        self.complete_error: RuntimeError | None = None
        self.completed_job_id: int | None = None
        self.failed_error: str | None = None
        self.claim_next_owner_types: tuple[str, ...] | None = None
        self.claim_owner_types: tuple[str, ...] | None = None

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: int = 30,
        owner_types: tuple[str, ...] | None = None,
    ) -> dict[str, object] | None:
        self.claim_next_owner_types = owner_types
        if self._job is None:
            return None
        claimed = dict(self._job)
        claimed["status"] = "RUNNING"
        claimed["lease_owner"] = worker_id
        return claimed

    def claim(
        self,
        job_id: int,
        *,
        worker_id: str,
        lease_seconds: int = 30,
        owner_types: tuple[str, ...] | None = None,
    ) -> dict[str, object] | None:
        self.claim_owner_types = owner_types
        claimed = self.claim_next(worker_id=worker_id, lease_seconds=lease_seconds, owner_types=owner_types)
        if claimed is None or int(claimed["id"]) != job_id:
            return None
        return claimed

    def complete(self, job_id: int, *, worker_id: str, lease_token: str | None = None) -> dict[str, object]:
        self.completed_job_id = job_id
        if self.complete_error is not None:
            raise self.complete_error
        return {"id": job_id, "status": "COMPLETED", "lease_owner": worker_id}

    def get(self, job_id: int) -> dict[str, object] | None:
        if self.current_job is not None and int(self.current_job["id"]) == job_id:
            return self.current_job
        return None

    def fail(
        self,
        job_id: int,
        *,
        worker_id: str,
        error: str,
        lease_token: str | None = None,
    ) -> dict[str, object]:
        self.failed_error = error
        return {
            "id": job_id,
            "run_id": int((self._job or {}).get("run_id") or 0),
            "status": "FAILED",
            "lease_owner": worker_id,
            "last_error": error,
        }


if __name__ == "__main__":
    unittest.main()
