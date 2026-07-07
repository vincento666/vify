from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository
from tests.support.mysql import mysql8_session


def test_runtime_job_dlq_query_retry_and_ignore_actions() -> None:
    with mysql8_session("runtime_jobs_dlq_actions", register=register_baseline_tables) as session:
        repository = RuntimeJobRepository(session)
        first = _failed_job(repository, run_id=25_001, owner_id=35_001, error="provider timeout")
        second = _failed_job(repository, run_id=25_002, owner_id=35_002, error="tool failed")
        third = _failed_job(repository, run_id=25_003, owner_id=35_003, error="manual fix applied")

        dlq = repository.list_dlq(owner_types=("WORKFLOW",))

        assert [item["id"] for item in dlq] == [first["id"], second["id"], third["id"]]
        assert [item["last_error"] for item in dlq] == ["provider timeout", "tool failed", "manual fix applied"]

        retried = repository.retry_dlq(int(first["id"]))

        assert retried["status"] == "QUEUED"
        assert retried["available_at"] is None
        assert retried["finished_at"] is None
        assert retried["lease_owner"] == ""
        assert retried["lease_token"] == ""
        assert retried["last_error"] == "provider timeout"

        ignored = repository.ignore_dlq(int(second["id"]), reason="operator accepted loss")

        assert ignored["status"] == "IGNORED"
        assert ignored["last_error"] == "operator accepted loss"

        resolved = repository.mark_dlq_resolved(int(third["id"]), reason="operator verified upstream fix")

        assert resolved["status"] == "RESOLVED"
        assert resolved["last_error"] == "operator verified upstream fix"
        assert [item["id"] for item in repository.list_dlq(owner_types=("WORKFLOW",))] == []


def _failed_job(repository: RuntimeJobRepository, *, run_id: int, owner_id: int, error: str) -> dict[str, object]:
    created = repository.enqueue(run_id=run_id, owner_type="WORKFLOW", owner_id=owner_id, max_attempts=1)
    claimed = repository.claim_next(worker_id=f"worker-{run_id}", lease_seconds=30)
    assert claimed is not None
    failed = repository.fail(
        int(created["id"]),
        worker_id=f"worker-{run_id}",
        lease_token=str(claimed["lease_token"]),
        error=error,
    )
    assert failed["status"] == "FAILED"
    return failed
