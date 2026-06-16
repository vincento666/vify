import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
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


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "customer_assistant.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    register_customer_assistant_tables()
    Base.metadata.create_all(bind=engine, tables=customer_assistant_tables())
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    session.info["_tmp_dir"] = tmp_dir
    return session
