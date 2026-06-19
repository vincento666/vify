import unittest
from datetime import datetime, timedelta

import sqlalchemy as sa

from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository
from tests.support.mysql import mysql8_session


class RuntimeJobRepositoryTest(unittest.TestCase):
    def test_claim_heartbeat_complete_and_expired_lease_takeover(self) -> None:
        with mysql8_session("runtime_jobs", register=register_baseline_tables) as session:
            repository = RuntimeJobRepository(session)
            created = repository.enqueue(
                run_id=101,
                owner_type="WORKFLOW",
                owner_id=202,
                job_type="runtime_v2_completion",
                payload={"source": "test"},
                max_attempts=3,
            )

            claimed = repository.claim_next(worker_id="worker-a", lease_seconds=30)
            self.assertIsNotNone(claimed)
            assert claimed is not None
            self.assertEqual(claimed["id"], created["id"])
            self.assertEqual(claimed["status"], "RUNNING")
            self.assertEqual(claimed["lease_owner"], "worker-a")
            self.assertEqual(claimed["attempt_count"], 1)
            self.assertIsNone(repository.claim_next(worker_id="worker-b", lease_seconds=30))

            heartbeat = repository.heartbeat(int(created["id"]), worker_id="worker-a", lease_seconds=60)
            self.assertGreater(heartbeat["lease_expires_at"], claimed["lease_expires_at"])

            job_table = sa.Table("runtime_jobs", sa.MetaData(), autoload_with=session.get_bind())
            session.execute(
                job_table.update()
                .where(job_table.c.id == int(created["id"]))
                .values(lease_expires_at=datetime.now() - timedelta(seconds=1))
            )
            session.commit()

            takeover = repository.claim_next(worker_id="worker-b", lease_seconds=30)
            self.assertIsNotNone(takeover)
            assert takeover is not None
            self.assertEqual(takeover["id"], created["id"])
            self.assertEqual(takeover["lease_owner"], "worker-b")
            self.assertEqual(takeover["attempt_count"], 2)

            completed = repository.complete(int(created["id"]), worker_id="worker-b")
            self.assertEqual(completed["status"], "COMPLETED")
            self.assertIsNotNone(completed["finished_at"])
            self.assertIsNone(repository.claim_next(worker_id="worker-c", lease_seconds=30))

    def test_failure_records_last_error_and_terminal_status(self) -> None:
        with mysql8_session("runtime_jobs_failure", register=register_baseline_tables) as session:
            repository = RuntimeJobRepository(session)
            created = repository.enqueue(
                run_id=303,
                owner_type="WORKFLOW",
                owner_id=404,
                job_type="runtime_v2_completion",
            )
            claimed = repository.claim_next(worker_id="worker-a", lease_seconds=30)
            self.assertEqual(claimed["id"], created["id"])

            failed = repository.fail(int(created["id"]), worker_id="worker-a", error="boom")

            self.assertEqual(failed["status"], "FAILED")
            self.assertEqual(failed["last_error"], "boom")
            self.assertIsNotNone(failed["finished_at"])


if __name__ == "__main__":
    unittest.main()
