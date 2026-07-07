from __future__ import annotations

from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository
from tests.support.mysql import Mysql8TestDatabase


def test_db_reconnect_after_pool_dispose_keeps_runtime_job_claim_and_complete_working() -> None:
    with Mysql8TestDatabase("runtime_chaos_db_reconnect") as database:
        database.create_all(register=register_baseline_tables)
        with database.session() as session:
            created = RuntimeJobRepository(session).enqueue(
                run_id=221_700_001,
                owner_type="WORKFLOW",
                owner_id=221_700,
            )

        assert database.engine is not None
        database.engine.dispose()

        with database.session() as session:
            repository = RuntimeJobRepository(session)
            claimed = repository.claim_next(worker_id="db-reconnect-worker", lease_seconds=30)
            assert claimed is not None
            assert int(claimed["id"]) == int(created["id"])
            completed = repository.complete(
                int(claimed["id"]),
                worker_id="db-reconnect-worker",
                lease_token=str(claimed["lease_token"]),
            )

        assert completed["status"] == "COMPLETED"
        assert completed["lease_owner"] == "db-reconnect-worker"
