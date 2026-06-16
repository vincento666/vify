import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.main import app
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)


class CustomerAssistantRuntimeE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "customer_assistant_runtime_e2e.db"
        self._engine = create_engine(f"sqlite:///{db_path}", future=True)
        register_customer_assistant_tables()
        Base.metadata.create_all(bind=self._engine, tables=customer_assistant_tables())
        self._factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, expire_on_commit=False)
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_refund_and_baggage_multitask_resume_proposed_action_and_events(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/customer-assistant/sessions", json={}).json()["data"]["id"]
            first = _turn(client, session_id, "我要退票，也想问行李额", "multi-1")
            replay = _turn(client, session_id, "我要退票，也想问行李额", "multi-1")
            continued = _turn(client, session_id, "订单号 TK-100", "multi-2")
            completed = _turn(client, session_id, "确认", "multi-3")
            replay_completed = _turn(client, session_id, "确认", "multi-3")
            tasks = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/tasks").json()["data"]["list"]
            events = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/events").json()["data"]["list"]

        self.assertEqual([summary["taskKey"] for summary in first["taskSummaries"]], ["refund_ticket", "baggage_qa"])
        self.assertEqual([summary["status"] for summary in first["taskSummaries"]], ["WAITING", "COMPLETED"])
        self.assertIn("订单号", first["customerReplyDraft"])
        self.assertIn("手提行李", first["customerReplyDraft"])
        self.assertEqual(replay["runId"], first["runId"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(continued["taskSummaries"][0]["checkpoint"]["currentStep"], "confirm")
        self.assertEqual(completed["proposedActions"][0]["status"], "PENDING")
        self.assertEqual(completed["proposedActions"][0]["actionType"], "submit_refund")
        self.assertEqual(replay_completed["proposedActions"], completed["proposedActions"])
        self.assertEqual([task["status"] for task in tasks], ["COMPLETED", "COMPLETED"])
        self.assertEqual(len(tasks[0]["proposedActions"]), 1)
        self.assertEqual([event["sequence"] for event in events], list(range(1, len(events) + 1)))
        event_types = [event["type"] for event in events]
        for required in (
            "run_started",
            "task_added",
            "task_waiting",
            "task_completed",
            "worker_started",
            "worker_result_received",
            "worker_proposed_action",
            "recommendation_generated",
            "run_completed",
        ):
            self.assertIn(required, event_types)
        worker_events = [event for event in events if event["type"] in {"worker_started", "worker_result_received"}]
        self.assertTrue(worker_events)
        self.assertTrue(all(event["spanId"] for event in worker_events))
        result_events = [event for event in events if event["type"] == "worker_result_received"]
        self.assertTrue(all(event["parentSpanId"] for event in result_events))

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


def _turn(client: TestClient, session_id: int, message: str, key: str) -> dict:
    response = client.post(
        f"/api/v1/customer-assistant/sessions/{session_id}/turns",
        json={"message": message, "idempotencyKey": key},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
