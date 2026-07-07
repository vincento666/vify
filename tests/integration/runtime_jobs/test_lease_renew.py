from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository
from tests.support.mysql import mysql8_session


def test_repeated_lease_renew_preserves_attempt_and_owner() -> None:
    with mysql8_session("runtime_jobs_lease_renew", register=register_baseline_tables) as session:
        repository = RuntimeJobRepository(session)
        created = repository.enqueue(run_id=22_001, owner_type="WORKFLOW", owner_id=32_001)
        claimed = repository.claim_next(worker_id="worker-a", lease_seconds=10)
        assert claimed is not None

        first = repository.heartbeat(
            int(created["id"]),
            worker_id="worker-a",
            lease_token=str(claimed["lease_token"]),
            lease_seconds=30,
        )
        second = repository.heartbeat(
            int(created["id"]),
            worker_id="worker-a",
            lease_token=str(claimed["lease_token"]),
            lease_seconds=60,
        )

        assert second["lease_owner"] == "worker-a"
        assert second["lease_token"] == claimed["lease_token"]
        assert second["attempt_count"] == 1
        assert second["lease_expires_at"] > first["lease_expires_at"]
