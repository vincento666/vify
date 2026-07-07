from contextlib import contextmanager
import unittest
from collections.abc import Iterator

from sqlalchemy.orm import Session

from tests.support.mysql import mysql8_session
from app.modules.runtime_lab.infra.repository import ActiveTaskConflict, RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabRepositoryTest(unittest.TestCase):
    def test_persists_session_task_event_and_command_replay_without_checkpoint_table(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)

            runtime_session = repository.create_session()
            first_event = repository.append_event(
                int(runtime_session["id"]),
                "SESSION_CREATED",
                {"source": "test"},
            )
            task = repository.create_task(
                int(runtime_session["id"]),
                sop_id="refund_ticket",
                current_step="collect_order_no",
            )
            task = repository.update_task_state(
                int(task["id"]),
                status="SUSPENDED",
                resume_summary="退票已收集订单号",
            )
            second_event = repository.append_event(
                int(runtime_session["id"]),
                "TASK_SUSPENDED",
                {"taskId": task["id"], "currentStep": "collect_order_no"},
            )
            command, replayed = repository.store_command_response(
                int(runtime_session["id"]),
                idempotency_key="msg-1",
                request_hash="hash-1",
                response_payload={"reply": "ok"},
            )
            replayed_command, replayed_again = repository.store_command_response(
                int(runtime_session["id"]),
                idempotency_key="msg-1",
                request_hash="hash-1",
                response_payload={"reply": "ignored"},
            )

            self.assertEqual(first_event["sequence"], 1)
            self.assertEqual(second_event["sequence"], 2)
            self.assertEqual(task["status"], "SUSPENDED")
            self.assertNotIn("checkpoint_id", task)
            listed_task = repository.list_tasks(int(runtime_session["id"]))[0]
            self.assertNotIn("business_refs", listed_task)
            self.assertNotIn("current_step", listed_task)
            self.assertEqual(repository.list_events(int(runtime_session["id"]))[-1]["event_type"], "TASK_SUSPENDED")
            self.assertFalse(replayed)
            self.assertTrue(replayed_again)
            self.assertEqual(command["id"], replayed_command["id"])
            self.assertEqual(replayed_command["response_payload"], {"reply": "ok"})

    def test_rejects_second_running_task_in_same_session(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            runtime_session = repository.create_session()
            repository.create_task(int(runtime_session["id"]), sop_id="refund_ticket")

            with self.assertRaises(ActiveTaskConflict):
                repository.create_task(int(runtime_session["id"]), sop_id="invoice_apply")


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_lab", register=register_runtime_lab_tables) as session:
        yield session
