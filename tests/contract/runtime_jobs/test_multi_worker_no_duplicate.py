from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Any

import sqlalchemy as sa

from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository
from tests.support.mysql import Mysql8TestDatabase


def test_multi_worker_claim_and_complete_has_no_duplicate_execution_under_stress() -> None:
    worker_count = 10
    job_count = 200

    with Mysql8TestDatabase("runtime_job_multi_worker_no_duplicate") as database:
        database.create_all(register=register_baseline_tables)
        with database.session() as session:
            repository = RuntimeJobRepository(session)
            for index in range(job_count):
                repository.enqueue(
                    run_id=221_300_000 + index,
                    owner_type="WORKFLOW",
                    owner_id=221_300,
                    priority=100,
                    max_attempts=1,
                )

        barrier = Barrier(worker_count)

        def drain(worker_index: int) -> list[dict[str, Any]]:
            barrier.wait(timeout=10)
            completed: list[dict[str, Any]] = []
            while True:
                with database.session() as session:
                    repository = RuntimeJobRepository(session)
                    claimed = repository.claim_next(
                        worker_id=f"worker-{worker_index}",
                        lease_seconds=30,
                        owner_types=("WORKFLOW",),
                    )
                    if claimed is None:
                        return completed
                    completed_job = repository.complete(
                        int(claimed["id"]),
                        worker_id=f"worker-{worker_index}",
                        lease_token=str(claimed["lease_token"]),
                    )
                    completed.append(
                        {
                            "job_id": int(claimed["id"]),
                            "run_id": int(claimed["run_id"]),
                            "worker_id": f"worker-{worker_index}",
                            "status": str(completed_job["status"]),
                        }
                    )

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            completed_by_worker = list(executor.map(drain, range(worker_count)))

        completed_claims = [claim for worker_claims in completed_by_worker for claim in worker_claims]
        completed_job_ids = [claim["job_id"] for claim in completed_claims]
        completed_run_ids = [claim["run_id"] for claim in completed_claims]

        assert len(completed_claims) == job_count
        assert len(set(completed_job_ids)) == job_count
        assert len(set(completed_run_ids)) == job_count
        assert {claim["status"] for claim in completed_claims} == {"COMPLETED"}

        job_table = sa.Table("runtime_jobs", sa.MetaData(), autoload_with=database.engine)
        with database.engine.connect() as connection:
            rows = connection.execute(
                sa.select(
                    job_table.c.id,
                    job_table.c.status,
                    job_table.c.attempt_count,
                    job_table.c.lease_owner,
                )
            ).mappings().all()

        assert len(rows) == job_count
        assert {row["status"] for row in rows} == {"COMPLETED"}
        assert {int(row["attempt_count"]) for row in rows} == {1}
        assert len({str(row["lease_owner"]) for row in rows}) == worker_count
