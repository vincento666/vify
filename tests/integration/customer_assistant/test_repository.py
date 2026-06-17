from contextlib import contextmanager
import unittest
from collections.abc import Iterator
from unittest.mock import patch

from sqlalchemy.orm import Session

from tests.support.mysql import mysql8_session
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)


class CustomerAssistantRepositoryTest(unittest.TestCase):
    def test_persists_session_run_task_events_actions_and_idempotency(self) -> None:
        with _session() as session:
            repository = CustomerAssistantRepository(session)

            assistant_session = repository.create_session(context={"customerId": "C-100"})
            run, replayed = repository.create_run(
                int(assistant_session["id"]),
                idempotency_key="turn-1",
                request_hash="hash-1",
                input_payload={"message": "我要退票"},
            )
            task = repository.upsert_task(
                session_id=int(assistant_session["id"]),
                task_key="refund_ticket",
                task_type="REFUND",
                business_key="refund_ticket",
                worker_type="chatflow_sop",
                worker_ref="refund_ticket",
                input_snapshot={"message": "我要退票"},
            )
            first_event = repository.append_event(
                session_id=int(assistant_session["id"]),
                run_id=int(run["id"]),
                event_type="run_started",
                payload={"message": "我要退票"},
            )
            second_event = repository.append_event(
                session_id=int(assistant_session["id"]),
                run_id=int(run["id"]),
                event_type="task_added",
                task_id=int(task["id"]),
                payload={"taskKey": "refund_ticket"},
            )
            action = repository.upsert_proposed_action(
                session_id=int(assistant_session["id"]),
                run_id=int(run["id"]),
                task_id=int(task["id"]),
                action_key="refund_ticket:submit_refund:TK-100",
                action_type="submit_refund",
                title="提交退票申请",
                payload={"orderNo": "TK-100"},
            )
            repository.complete_run(int(run["id"]), response_payload={"runId": run["id"]})
            replayed_run, replayed_again = repository.create_run(
                int(assistant_session["id"]),
                idempotency_key="turn-1",
                request_hash="hash-1",
                input_payload={"message": "我要退票"},
            )

            self.assertFalse(replayed)
            self.assertTrue(replayed_again)
            self.assertEqual(replayed_run["id"], run["id"])
            self.assertEqual(first_event["sequence"], 1)
            self.assertEqual(second_event["sequence"], 2)
            self.assertEqual(repository.list_events(int(assistant_session["id"]))[-1]["type"], "task_added")
            self.assertEqual(repository.list_tasks(int(assistant_session["id"]))[0]["task_key"], "refund_ticket")
            self.assertEqual(repository.list_proposed_actions(int(assistant_session["id"]))[0]["id"], action["id"])
            self.assertEqual(
                repository.get_run_by_idempotency(int(assistant_session["id"]), "turn-1")["response_payload"],
                {"runId": run["id"]},
            )

    def test_append_event_recovers_from_stale_sequence_after_concurrent_writer(self) -> None:
        with _session() as session:
            repository = CustomerAssistantRepository(session)
            assistant_session = repository.create_session(context={"customerId": "C-100"})
            repository.append_event(
                session_id=int(assistant_session["id"]),
                event_type="run_started",
                payload={"message": "first"},
            )

            with patch.object(repository, "_next_event_sequence", side_effect=[1, 2]):
                second_event = repository.append_event(
                    session_id=int(assistant_session["id"]),
                    event_type="task_added",
                    payload={"message": "second"},
                )

            self.assertEqual(second_event["sequence"], 2)
            self.assertEqual([event["sequence"] for event in repository.list_events(int(assistant_session["id"]))], [1, 2])

    def test_append_worker_event_recovers_from_stale_sequence_after_concurrent_writer(self) -> None:
        with _session() as session:
            repository = CustomerAssistantRepository(session)
            assistant_session = repository.create_session(context={"customerId": "C-100"})
            worker_run, _ = repository.create_worker_run(
                session_id=int(assistant_session["id"]),
                parent_run_id=1,
                task_id=1,
                worker_type="stub_qa",
                worker_ref="stub_qa",
                idempotency_key="worker-run-1",
                request_hash="hash-1",
                input_payload={"message": "first"},
            )

            with patch.object(repository, "_next_worker_event_sequence", side_effect=[1, 2]):
                second_event = repository.append_worker_event(
                    int(worker_run["id"]),
                    "worker_run_started",
                    {"workerRunId": worker_run["id"]},
                )

            self.assertEqual(second_event["sequence"], 2)
            self.assertEqual([event["sequence"] for event in repository.list_worker_events(int(worker_run["id"]))], [1, 2])

    def test_conditional_proposed_action_transition_rejects_stale_status(self) -> None:
        with _session() as session:
            repository = CustomerAssistantRepository(session)
            assistant_session = repository.create_session(context={"customerId": "C-200"})
            run, _ = repository.create_run(
                int(assistant_session["id"]),
                idempotency_key="transition-1",
                request_hash="transition-hash",
                input_payload={"message": "我要退票"},
            )
            action = repository.upsert_proposed_action(
                session_id=int(assistant_session["id"]),
                run_id=int(run["id"]),
                task_id=None,
                action_key="transition:submit_refund:TK-200",
                action_type="submit_refund",
                title="提交退票申请",
                payload={"orderNo": "TK-200"},
            )

            confirmed = repository.transition_proposed_action_status(
                int(action["id"]),
                expected_status="PENDING",
                next_status="CONFIRMED",
            )
            stale = repository.transition_proposed_action_status(
                int(action["id"]),
                expected_status="PENDING",
                next_status="EXECUTING",
            )
            current = repository.get_proposed_action(int(action["id"]))

        self.assertIsNotNone(confirmed)
        self.assertIsNone(stale)
        self.assertEqual(current["status"], "CONFIRMED")


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("customer_assistant", tables=customer_assistant_tables(), register=register_customer_assistant_tables) as session:
        yield session
