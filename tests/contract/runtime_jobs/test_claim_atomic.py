from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import sqlalchemy as sa

from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository
from tests.support.mysql import Mysql8TestDatabase


def test_runtime_job_claim_next_is_atomic_across_concurrent_workers() -> None:
    worker_count = 20

    with Mysql8TestDatabase("runtime_job_claim_atomic") as database:
        database.create_all(register=register_baseline_tables)
        with database.session() as session:
            repository = RuntimeJobRepository(session)
            for index in range(worker_count):
                repository.enqueue(
                    run_id=10_000 + index,
                    owner_type="WORKFLOW",
                    owner_id=20_000 + index,
                    priority=100,
                )

        barrier = Barrier(worker_count)

        def claim(worker_index: int) -> int | None:
            barrier.wait(timeout=10)
            with database.session() as session:
                claimed = RuntimeJobRepository(session).claim_next(
                    worker_id=f"worker-{worker_index}",
                    lease_seconds=30,
                    owner_types=("WORKFLOW",),
                )
                return int(claimed["id"]) if claimed is not None else None

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            claimed_ids = list(executor.map(claim, range(worker_count)))

        non_empty_claims = [job_id for job_id in claimed_ids if job_id is not None]
        assert len(non_empty_claims) == worker_count
        assert len(set(non_empty_claims)) == worker_count

        job_table = sa.Table("runtime_jobs", sa.MetaData(), autoload_with=database.engine)
        with database.engine.connect() as connection:
            rows = connection.execute(
                sa.select(job_table.c.id, job_table.c.status, job_table.c.attempt_count, job_table.c.lease_owner)
            ).mappings().all()

        assert len(rows) == worker_count
        assert {row["status"] for row in rows} == {"RUNNING"}
        assert {int(row["attempt_count"]) for row in rows} == {1}
        assert len({row["lease_owner"] for row in rows}) == worker_count
