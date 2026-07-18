import unittest
from datetime import datetime, timedelta

import sqlalchemy as sa

from app.core.schema import register_baseline_tables
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository
from tests.support.mysql import mysql8_session


class RuntimeJobRepositoryTest(unittest.TestCase):
    def test_same_run_and_job_type_can_exist_for_different_owner_types(self) -> None:
        with mysql8_session("runtime_jobs_owner_identity", register=register_baseline_tables) as session:
            repository = RuntimeJobRepository(session)

            workflow = repository.enqueue(
                run_id=101,
                owner_type="WORKFLOW",
                owner_id=201,
                job_type="runtime_v2_completion",
            )
            assistant = repository.enqueue(
                run_id=101,
                owner_type="AI_ASSISTANT",
                owner_id=301,
                job_type="runtime_v2_completion",
            )

            self.assertNotEqual(workflow["id"], assistant["id"])
            self.assertEqual(assistant["owner_type"], "AI_ASSISTANT")
            self.assertEqual(
                repository.get_by_run(
                    101,
                    owner_type="AI_ASSISTANT",
                    job_type="runtime_v2_completion",
                )["id"],
                assistant["id"],
            )

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
                max_attempts=1,
            )
            claimed = repository.claim_next(worker_id="worker-a", lease_seconds=30)
            self.assertEqual(claimed["id"], created["id"])

            failed = repository.fail(int(created["id"]), worker_id="worker-a", error="boom")

            self.assertEqual(failed["status"], "FAILED")
            self.assertEqual(failed["last_error"], "boom")
            self.assertIsNotNone(failed["finished_at"])

    def test_claim_next_filters_by_owner_type_and_preserves_lease_takeover(self) -> None:
        with mysql8_session("runtime_jobs_owner_filter", register=register_baseline_tables) as session:
            repository = RuntimeJobRepository(session)
            chatflow = repository.enqueue(run_id=501, owner_type="CHATFLOW", owner_id=601)
            workflow = repository.enqueue(run_id=502, owner_type="WORKFLOW", owner_id=602)

            claimed_workflow = repository.claim_next(
                worker_id="workflow-worker",
                lease_seconds=30,
                owner_types=("WORKFLOW",),
            )

            self.assertIsNotNone(claimed_workflow)
            assert claimed_workflow is not None
            self.assertEqual(claimed_workflow["id"], workflow["id"])
            self.assertEqual(claimed_workflow["owner_type"], "WORKFLOW")
            self.assertEqual(repository.get(int(chatflow["id"]))["status"], "QUEUED")

            claimed_chatflow = repository.claim_next(
                worker_id="chatflow-worker",
                lease_seconds=30,
                owner_types=("CHATFLOW",),
            )

            self.assertIsNotNone(claimed_chatflow)
            assert claimed_chatflow is not None
            self.assertEqual(claimed_chatflow["id"], chatflow["id"])
            self.assertEqual(claimed_chatflow["owner_type"], "CHATFLOW")

            job_table = sa.Table("runtime_jobs", sa.MetaData(), autoload_with=session.get_bind())
            session.execute(
                job_table.update()
                .where(job_table.c.id == int(chatflow["id"]))
                .values(lease_expires_at=datetime.now() - timedelta(seconds=1))
            )
            session.commit()

            self.assertIsNone(
                repository.claim(
                    int(chatflow["id"]),
                    worker_id="workflow-worker",
                    lease_seconds=30,
                    owner_types=("WORKFLOW",),
                )
            )
            takeover = repository.claim(
                int(chatflow["id"]),
                worker_id="chatflow-worker-b",
                lease_seconds=30,
                owner_types=("CHATFLOW",),
            )

            self.assertIsNotNone(takeover)
            assert takeover is not None
            self.assertEqual(takeover["lease_owner"], "chatflow-worker-b")


if __name__ == "__main__":
    unittest.main()
