from __future__ import annotations

from datetime import datetime, timedelta

import pytest
import sqlalchemy as sa

from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository
from tests.support.mysql import mysql8_session


def test_worker_crash_takeover_completes_jobs_without_stale_worker_writeback() -> None:
    crash_count = 10
    job_count = 20

    with mysql8_session("runtime_chaos_worker_crash", register=register_baseline_tables) as session:
        repository = RuntimeJobRepository(session)
        for index in range(job_count):
            repository.enqueue(
                run_id=221_600_000 + index,
                owner_type="WORKFLOW",
                owner_id=221_600,
                max_attempts=1,
            )

        crashed_jobs: list[dict[str, object]] = []
        for index in range(crash_count):
            crashed = repository.claim_next(worker_id=f"crashed-worker-{index}", lease_seconds=1)
            assert crashed is not None
            crashed_jobs.append(crashed)
            _expire_lease(session, int(crashed["id"]))

            takeover = repository.claim_next(worker_id=f"takeover-worker-{index}", lease_seconds=30)
            assert takeover is not None
            assert int(takeover["id"]) == int(crashed["id"])
            assert takeover["lease_token"] != crashed["lease_token"]

            with pytest.raises(RuntimeError, match="lease"):
                repository.complete(
                    int(crashed["id"]),
                    worker_id=f"crashed-worker-{index}",
                    lease_token=str(crashed["lease_token"]),
                )

            completed = repository.complete(
                int(takeover["id"]),
                worker_id=f"takeover-worker-{index}",
                lease_token=str(takeover["lease_token"]),
            )
            assert completed["status"] == "COMPLETED"

        while True:
            claimed = repository.claim_next(worker_id="steady-worker", lease_seconds=30)
            if claimed is None:
                break
            repository.complete(
                int(claimed["id"]),
                worker_id="steady-worker",
                lease_token=str(claimed["lease_token"]),
            )

        job_table = sa.Table("runtime_jobs", sa.MetaData(), autoload_with=session.get_bind())
        rows = session.execute(sa.select(job_table)).mappings().all()

        assert len(rows) == job_count
        assert {row["status"] for row in rows} == {"COMPLETED"}
        assert {int(row["attempt_count"]) for row in rows} == {1, 2}
        assert sum(1 for row in rows if int(row["attempt_count"]) == 2) == crash_count
        assert {int(job["id"]) for job in crashed_jobs} <= {int(row["id"]) for row in rows}


def _expire_lease(session: object, job_id: int) -> None:
    job_table = sa.Table("runtime_jobs", sa.MetaData(), autoload_with=session.get_bind())
    session.execute(
        job_table.update()
        .where(job_table.c.id == job_id)
        .values(lease_expires_at=datetime.now() - timedelta(seconds=1))
    )
    session.commit()
