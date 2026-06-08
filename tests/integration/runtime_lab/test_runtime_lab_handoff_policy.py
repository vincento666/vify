import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabHandoffPolicyTest(unittest.TestCase):
    def test_active_sop_explicit_handoff_is_hard_stop_and_preserves_task_state(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            started = service.handle_message(session_id, "我要退票")
            handoff = service.handle_message(session_id, "我要人工客服")

            self.assertEqual(started.route_decision.action, "START_SOP")
            self.assertEqual(handoff.route_decision.action, "HANDOFF_TO_HUMAN")
            self.assertEqual(handoff.route_decision.handoff["reasonCode"], "USER_REQUEST")
            self.assertEqual(handoff.active_task["id"], started.active_task["id"])
            self.assertEqual(handoff.active_task["sop_id"], "refund_ticket")
            self.assertEqual(handoff.active_task["current_step"], "collect_order_no")
            self.assertEqual(handoff.suspended_tasks, [])

    def test_handoff_emits_events_context_snapshot_and_user_reply(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要退票")
            switched = service.handle_message(session_id, "我要开发票")
            handoff = service.handle_message(session_id, "我要投诉，转人工")

            self.assertEqual(switched.route_decision.action, "SUSPEND_AND_START")
            self.assertEqual(handoff.reply, "已为您转接人工客服，请稍候。")
            self.assertEqual(handoff.route_decision.action, "HANDOFF_TO_HUMAN")
            self.assertEqual(handoff.active_task["sop_id"], "invoice_apply")
            self.assertEqual(handoff.suspended_tasks[0]["sop_id"], "refund_ticket")

            event_types = [event["event_type"] for event in handoff.events]
            self.assertIn("HANDOFF_DECIDED", event_types)
            self.assertIn("HANDOFF_REQUESTED", event_types)
            requested = next(event for event in handoff.events if event["event_type"] == "HANDOFF_REQUESTED")
            snapshot = requested["payload"]["contextSnapshot"]
            self.assertEqual(snapshot["sourceLayer"], "explicit_signal")
            self.assertEqual(snapshot["reasonCode"], "USER_REQUEST")
            self.assertEqual(snapshot["userMessage"], "我要投诉，转人工")
            self.assertEqual(snapshot["activeTaskSummary"]["sopId"], "invoice_apply")
            self.assertEqual(snapshot["suspendedTaskSummaries"][0]["sopId"], "refund_ticket")
            self.assertEqual(snapshot["routeEvidence"]["action"], "HANDOFF_TO_HUMAN")
            self.assertEqual(snapshot["recentTranscript"][-1]["content"], "我要投诉，转人工")
            self.assertEqual(requested["payload"]["ticketId"], None)

    def test_configured_handoff_service_receives_one_way_context_snapshot(self) -> None:
        with _session() as session:
            handoff_service = _RecordingHandoffService()
            service = RuntimeLabService(RuntimeLabRepository(session), handoff_service=handoff_service)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要退票")
            handoff = service.handle_message(session_id, "我要人工客服")

            self.assertEqual(handoff.route_decision.action, "HANDOFF_TO_HUMAN")
            self.assertEqual(len(handoff_service.created_tickets), 1)
            ticket_payload = handoff_service.created_tickets[0]
            self.assertEqual(ticket_payload["session_id"], str(session_id))
            self.assertEqual(ticket_payload["reason"], "USER_REQUEST")
            self.assertEqual(ticket_payload["priority"], "high")
            self.assertEqual(ticket_payload["context_snapshot"]["activeTaskSummary"]["sopId"], "refund_ticket")
            self.assertEqual(ticket_payload["transcript_snapshot"][-1]["content"], "我要人工客服")


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "runtime_lab_handoff_policy.db"
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


class _RecordingHandoffService:
    def __init__(self) -> None:
        self.created_tickets: list[dict[str, object]] = []

    def create_ticket(self, data: dict[str, object]) -> dict[str, object]:
        self.created_tickets.append(data)
        return {"id": 88, "status": "queued"}
