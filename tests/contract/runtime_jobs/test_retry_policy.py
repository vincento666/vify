from datetime import datetime, timedelta

import sqlalchemy as sa

from app.core.schema import register_baseline_tables
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository
from tests.support.mysql import mysql8_session


def test_runtime_job_failure_requeues_with_backoff_before_max_attempts() -> None:
    with mysql8_session("runtime_jobs_retry_policy", register=register_baseline_tables) as session:
        repository = RuntimeJobRepository(session)
        created = repository.enqueue(run_id=24_001, owner_type="WORKFLOW", owner_id=34_001, max_attempts=3)
        claimed = repository.claim_next(worker_id="worker-a", lease_seconds=30)
        assert claimed is not None

        failed = repository.fail(
            int(created["id"]),
            worker_id="worker-a",
            lease_token=str(claimed["lease_token"]),
            error="temporary provider timeout",
            retry_backoff_seconds=(10, 30, 90),
        )

        assert failed["status"] == "QUEUED"
        assert failed["attempt_count"] == 1
        assert failed["max_attempts"] == 3
        assert failed["last_error"] == "temporary provider timeout"
        assert failed["available_at"] >= datetime.now() + timedelta(seconds=8)
        assert failed["lease_owner"] == ""
        assert failed["lease_token"] == ""
        assert failed["lease_expires_at"] is None
        assert failed["finished_at"] is None


def test_runtime_job_retry_backoff_uses_attempt_number_sequence() -> None:
    with mysql8_session("runtime_jobs_retry_backoff", register=register_baseline_tables) as session:
        repository = RuntimeJobRepository(session)
        created = repository.enqueue(run_id=24_002, owner_type="WORKFLOW", owner_id=34_002, max_attempts=4)
        first = repository.claim_next(worker_id="worker-a", lease_seconds=30)
        assert first is not None
        first_failure = repository.fail(
            int(created["id"]),
            worker_id="worker-a",
            lease_token=str(first["lease_token"]),
            error="first failure",
            retry_backoff_seconds=(5, 40, 120),
        )

        job_table = sa.Table("runtime_jobs", sa.MetaData(), autoload_with=session.get_bind())
        session.execute(
            job_table.update()
            .where(job_table.c.id == int(created["id"]))
            .values(available_at=datetime.now() - timedelta(seconds=1))
        )
        session.commit()

        second = repository.claim_next(worker_id="worker-b", lease_seconds=30)
        assert second is not None
        second_failure = repository.fail(
            int(created["id"]),
            worker_id="worker-b",
            lease_token=str(second["lease_token"]),
            error="second failure",
            retry_backoff_seconds=(5, 40, 120),
        )

        assert first_failure["attempt_count"] == 1
        assert second_failure["attempt_count"] == 2
        assert second_failure["available_at"] >= datetime.now() + timedelta(seconds=35)
        assert second_failure["last_error"] == "second failure"


def test_runtime_job_failure_at_max_attempts_is_terminal() -> None:
    with mysql8_session("runtime_jobs_retry_terminal", register=register_baseline_tables) as session:
        repository = RuntimeJobRepository(session)
        created = repository.enqueue(run_id=24_003, owner_type="WORKFLOW", owner_id=34_003, max_attempts=1)
        claimed = repository.claim_next(worker_id="worker-a", lease_seconds=30)
        assert claimed is not None

        failed = repository.fail(
            int(created["id"]),
            worker_id="worker-a",
            lease_token=str(claimed["lease_token"]),
            error="permanent failure",
            retry_backoff_seconds=(10, 30, 90),
        )

        assert failed["status"] == "FAILED"
        assert failed["attempt_count"] == 1
        assert failed["last_error"] == "permanent failure"
        assert failed["available_at"] is None
        assert failed["finished_at"] is not None
