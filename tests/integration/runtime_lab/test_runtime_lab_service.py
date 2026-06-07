import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabServiceTest(unittest.TestCase):
    def test_interruptible_switch_suspends_active_task_and_offers_resume_after_completion(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()

            started = service.handle_message(int(runtime_session["id"]), "我要退票")
            switched = service.handle_message(int(runtime_session["id"]), "我要开发票")
            service.handle_message(int(runtime_session["id"]), "INV-200")
            completed = service.handle_message(int(runtime_session["id"]), "确认")

            self.assertEqual(started.route_decision.action, "START_SOP")
            self.assertEqual(switched.route_decision.action, "SUSPEND_AND_START")
            self.assertEqual(switched.active_task["sop_id"], "invoice_apply")
            self.assertEqual(switched.suspended_tasks[0]["sop_id"], "refund_ticket")
            self.assertEqual(completed.route_decision.action, "COMPLETE_TASK")
            self.assertIsNotNone(completed.resume_offer)
            self.assertEqual(completed.resume_offer["taskId"], switched.suspended_tasks[0]["id"])
            self.assertEqual(
                [event["event_type"] for event in completed.events],
                [
                    "SESSION_CREATED",
                    "USER_MESSAGE",
                    "ROUTE_DECISION",
                    "TASK_STARTED",
                    "USER_MESSAGE",
                    "ROUTE_DECISION",
                    "TASK_SUSPENDED",
                    "TASK_STARTED",
                    "USER_MESSAGE",
                    "ROUTE_DECISION",
                    "TASK_CONTINUED",
                    "USER_MESSAGE",
                    "ROUTE_DECISION",
                    "TASK_COMPLETED",
                    "RESUME_OFFERED",
                ],
            )

    def test_rejects_switch_at_confirm_step_and_when_one_task_already_suspended(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()

            service.handle_message(int(runtime_session["id"]), "我要退票")
            service.handle_message(int(runtime_session["id"]), "TK-100")
            rejected_at_confirm = service.handle_message(int(runtime_session["id"]), "我要改签")

            self.assertEqual(rejected_at_confirm.route_decision.action, "REJECT_SWITCH_CONTINUE_ACTIVE")
            self.assertEqual(rejected_at_confirm.active_task["sop_id"], "refund_ticket")
            self.assertEqual(rejected_at_confirm.active_task["current_step"], "confirm")
            self.assertEqual(len(rejected_at_confirm.suspended_tasks), 0)

        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()

            service.handle_message(int(runtime_session["id"]), "我要退票")
            service.handle_message(int(runtime_session["id"]), "我要开发票")
            rejected_by_limit = service.handle_message(int(runtime_session["id"]), "我要改签")

            self.assertEqual(rejected_by_limit.route_decision.action, "REJECT_SWITCH_SUSPENDED_LIMIT")
            self.assertEqual(rejected_by_limit.active_task["sop_id"], "invoice_apply")
            self.assertEqual([task["sop_id"] for task in rejected_by_limit.suspended_tasks], ["refund_ticket"])

    def test_resume_offer_phrases_restore_suspended_task_checkpoint(self) -> None:
        for phrase in ("继续", "继续刚才", "继续第一个"):
            with self.subTest(phrase=phrase):
                with _session() as session:
                    service = RuntimeLabService(RuntimeLabRepository(session))
                    runtime_session = service.create_session()

                    service.handle_message(int(runtime_session["id"]), "我要退票")
                    service.handle_message(int(runtime_session["id"]), "我要开发票")
                    service.handle_message(int(runtime_session["id"]), "INV-200")
                    service.handle_message(int(runtime_session["id"]), "确认")
                    resumed = service.handle_message(int(runtime_session["id"]), phrase)

                    self.assertEqual(resumed.route_decision.action, "RESUME_TASK")
                    self.assertEqual(resumed.active_task["sop_id"], "refund_ticket")
                    self.assertEqual(resumed.active_task["current_step"], "collect_order_no")
                    self.assertEqual(resumed.suspended_tasks, [])
                    self.assertIsNone(resumed.resume_offer)
                    self.assertEqual(resumed.events[-1]["event_type"], "TASK_RESUMED")


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "runtime_lab_service.db"
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
