from datetime import datetime, timedelta

import pytest
import sqlalchemy as sa

from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository
from tests.support.mysql import mysql8_session


def test_expired_lease_takeover_invalidates_crashed_worker_completion() -> None:
    with mysql8_session("runtime_jobs_crash_takeover", register=register_baseline_tables) as session:
        repository = RuntimeJobRepository(session)
        created = repository.enqueue(run_id=23_001, owner_type="WORKFLOW", owner_id=33_001)
        crashed = repository.claim_next(worker_id="worker-a", lease_seconds=1)
        assert crashed is not None

        job_table = sa.Table("runtime_jobs", sa.MetaData(), autoload_with=session.get_bind())
        session.execute(
            job_table.update()
            .where(job_table.c.id == int(created["id"]))
            .values(lease_expires_at=datetime.now() - timedelta(seconds=1))
        )
        session.commit()

        takeover = repository.claim_next(worker_id="worker-b", lease_seconds=30)
        assert takeover is not None
        assert takeover["id"] == created["id"]
        assert takeover["lease_owner"] == "worker-b"
        assert takeover["lease_token"] != crashed["lease_token"]

        with pytest.raises(RuntimeError, match="lease"):
            repository.complete(
                int(created["id"]),
                worker_id="worker-a",
                lease_token=str(crashed["lease_token"]),
            )

        current = repository.get(int(created["id"]))
        assert current is not None
        assert current["status"] == "RUNNING"
        assert current["lease_owner"] == "worker-b"
