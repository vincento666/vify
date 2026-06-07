import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.runtime_lab.infra.repository import ActiveTaskConflict, RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabRepositoryTest(unittest.TestCase):
    def test_persists_session_task_checkpoint_event_and_command_replay(self) -> None:
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
            checkpoint = repository.create_checkpoint(
                int(runtime_session["id"]),
                int(task["id"]),
                sop_id="refund_ticket",
                current_step="collect_order_no",
                pending_prompt="请提供订单号",
                collected={"order_no": "TK-100"},
                scoped_variables={"__chatflow": {"runId": 123}, "conversation.order_no": "TK-100"},
            )
            task = repository.update_task_state(
                int(task["id"]),
                status="SUSPENDED",
                checkpoint_id=int(checkpoint["id"]),
                resume_summary="退票已收集订单号",
            )
            second_event = repository.append_event(
                int(runtime_session["id"]),
                "TASK_SUSPENDED",
                {"taskId": task["id"]},
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
            self.assertEqual(task["checkpoint_id"], checkpoint["id"])
            self.assertEqual(
                repository.get_latest_checkpoint(int(task["id"]))["scoped_variables"]["__chatflow"]["runId"],
                123,
            )
            self.assertEqual(repository.list_tasks(int(runtime_session["id"]))[0]["business_refs"], {})
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


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "runtime_lab.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    register_runtime_lab_tables()
    tables = [
        Base.metadata.tables["runtime_lab_session"],
        Base.metadata.tables["runtime_lab_task"],
        Base.metadata.tables["runtime_lab_checkpoint"],
        Base.metadata.tables["runtime_lab_event"],
        Base.metadata.tables["runtime_lab_command"],
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    session.info["_tmp_dir"] = tmp_dir
    return session
