import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)


class CustomerAssistantRuntimeE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(self, "customer_assistant_runtime_e2e", tables=customer_assistant_tables(), register=register_customer_assistant_tables)
        self._engine = self._database.engine
        self._factory = self._database.session_factory
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
        self.assertEqual([summary["status"] for summary in first["taskSummaries"]], ["WAITING", "RUNNING"])
        self.assertIn("订单号", first["customerReplyDraft"])
        self.assertTrue(first["taskSummaries"][1]["workerAsyncRefs"]["supported"])
        self.assertIn("required worker evidence is pending", " ".join(first["warnings"]))
        self.assertEqual(replay["runId"], first["runId"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(continued["taskSummaries"][0]["checkpoint"]["currentStep"], "confirm")
        self.assertEqual(continued["taskSummaries"][1]["status"], "COMPLETED")
        self.assertEqual(completed["proposedActions"][0]["status"], "PENDING")
        self.assertEqual(completed["proposedActions"][0]["actionType"], "submit_refund")
        self.assertEqual(replay_completed["proposedActions"], completed["proposedActions"])
        self.assertEqual([task["status"] for task in tasks], ["COMPLETED", "COMPLETED"])
        self.assertEqual(len(tasks[0]["proposedActions"]), 1)
        baggage_task = next(task for task in tasks if task["taskKey"] == "baggage_qa")
        self.assertIn("手提行李", baggage_task["lastResult"]["customerReplyDraft"])
        self.assertEqual([event["sequence"] for event in events], list(range(1, len(events) + 1)))
        event_types = [event["type"] for event in events]
        for required in (
            "run_started",
            "task_added",
            "task_waiting",
            "task_completed",
            "worker_started",
            "worker_run_pending",
            "worker_result_received",
            "worker_result_consumed",
            "worker_proposed_action",
            "recommendation_generated",
            "run_completed",
        ):
            self.assertIn(required, event_types)
        worker_started_events = [event for event in events if event["type"] == "worker_started"]
        self.assertTrue(worker_started_events)
        self.assertTrue(all(event["spanId"] for event in worker_started_events))
        result_events = [event for event in events if event["type"] == "worker_result_received"]
        traced_result_events = [
            event
            for event in result_events
            if event["observability"].get("sourceKind") in {"chatflow", "worker"}
            and event["payload"].get("workerRunId")
        ]
        compatibility_result_events = [
            event
            for event in result_events
            if event["observability"].get("sourceKind") == "assistant"
        ]
        self.assertTrue(traced_result_events)
        self.assertTrue(all(event["parentSpanId"] for event in traced_result_events))
        self.assertTrue(compatibility_result_events)

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
