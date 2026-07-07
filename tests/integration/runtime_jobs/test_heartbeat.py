from datetime import timedelta

import pytest

from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository
from tests.support.mysql import mysql8_session


def test_heartbeat_requires_current_worker_and_lease_token() -> None:
    with mysql8_session("runtime_jobs_heartbeat", register=register_baseline_tables) as session:
        repository = RuntimeJobRepository(session)
        created = repository.enqueue(run_id=21_001, owner_type="WORKFLOW", owner_id=31_001)
        claimed = repository.claim_next(worker_id="worker-a", lease_seconds=30)
        assert claimed is not None

        with pytest.raises(RuntimeError, match="lease"):
            repository.heartbeat(int(created["id"]), worker_id="worker-a", lease_token="stale-token")

        unchanged = repository.get(int(created["id"]))
        assert unchanged is not None
        assert unchanged["lease_token"] == claimed["lease_token"]
        assert unchanged["lease_expires_at"] == claimed["lease_expires_at"]


def test_heartbeat_extends_current_lease_and_records_heartbeat_time() -> None:
    with mysql8_session("runtime_jobs_heartbeat_renew", register=register_baseline_tables) as session:
        repository = RuntimeJobRepository(session)
        created = repository.enqueue(run_id=21_002, owner_type="WORKFLOW", owner_id=31_002)
        claimed = repository.claim_next(worker_id="worker-a", lease_seconds=30)
        assert claimed is not None

        renewed = repository.heartbeat(
            int(created["id"]),
            worker_id="worker-a",
            lease_token=str(claimed["lease_token"]),
            lease_seconds=90,
        )

        assert renewed["lease_owner"] == "worker-a"
        assert renewed["lease_token"] == claimed["lease_token"]
        assert renewed["lease_expires_at"] >= claimed["lease_expires_at"] + timedelta(seconds=50)
        assert renewed["last_heartbeat_at"] is not None
