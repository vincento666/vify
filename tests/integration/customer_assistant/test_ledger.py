import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.customer_assistant.domain.ledger import CustomerAssistantLedger
from app.modules.customer_assistant.domain.models import TaskCommand, TaskCommandType, TaskStatus, WorkerResult
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)


class CustomerAssistantLedgerTest(unittest.TestCase):
    def test_applies_task_commands_and_worker_result_updates(self) -> None:
        with _session() as session:
            repository = CustomerAssistantRepository(session)
            assistant_session = repository.create_session()
            run, _ = repository.create_run(
                int(assistant_session["id"]),
                idempotency_key="ledger-1",
                request_hash="hash",
                input_payload={"message": "我要退票，也问行李"},
            )
            ledger = CustomerAssistantLedger(repository)

            created = ledger.apply_commands(
                int(assistant_session["id"]),
                int(run["id"]),
                "我要退票，也问行李",
                [
                    TaskCommand(
                        TaskCommandType.ADD_TASK,
                        task_key="refund_ticket",
                        task_type="REFUND",
                        business_key="refund_ticket",
                        worker_type="chatflow_sop",
                        worker_ref="refund_ticket",
                    ),
                    TaskCommand(
                        TaskCommandType.ADD_TASK,
                        task_key="baggage_qa",
                        task_type="QA",
                        business_key="baggage_qa",
                        worker_type="stub_qa",
                        worker_ref="baggage_allowance",
                    ),
                ],
            )
            retained = ledger.apply_commands(
                int(assistant_session["id"]),
                int(run["id"]),
                "订单号 TK-100",
                [TaskCommand(TaskCommandType.RETAIN_TASK, task_key="refund_ticket")],
            )
            cancelled = ledger.apply_commands(
                int(assistant_session["id"]),
                int(run["id"]),
                "取消退票",
                [TaskCommand(TaskCommandType.CANCEL_TASK, task_key="refund_ticket")],
            )
            updated = ledger.apply_worker_results(
                int(assistant_session["id"]),
                int(run["id"]),
                [
                    WorkerResult(
                        task_id=int(created.ready_tasks[1].id or 0),
                        worker_type="stub_qa",
                        status=TaskStatus.COMPLETED,
                        customer_reply_draft="可免费携带一件手提行李。",
                    )
                ],
            )

            tasks = repository.list_tasks(int(assistant_session["id"]))
            events = repository.list_events(int(assistant_session["id"]))

            self.assertEqual([task["task_key"] for task in tasks], ["refund_ticket", "baggage_qa"])
            self.assertEqual([task["status"] for task in tasks], ["CANCELLED", "COMPLETED"])
            self.assertEqual([task.task_key for task in created.ready_tasks], ["refund_ticket", "baggage_qa"])
            self.assertEqual([task.task_key for task in retained.ready_tasks], ["refund_ticket"])
            self.assertEqual(cancelled.ready_tasks, ())
            self.assertEqual(updated[0].last_result["customerReplyDraft"], "可免费携带一件手提行李。")
            self.assertEqual(
                [event["type"] for event in events],
                ["task_added", "task_added", "task_retained", "task_cancelled", "task_completed"],
            )


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "customer_assistant_ledger.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    register_customer_assistant_tables()
    Base.metadata.create_all(bind=engine, tables=customer_assistant_tables())
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    session.info["_tmp_dir"] = tmp_dir
    return session


if __name__ == "__main__":
    unittest.main()
