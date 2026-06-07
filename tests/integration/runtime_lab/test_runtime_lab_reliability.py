import unittest

from fastapi.testclient import TestClient

from app.main import app


class RuntimeLabReliabilityTest(unittest.TestCase):
    def test_duplicate_idempotency_key_replays_without_duplicate_task_or_events(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
            first = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "我要退票", "idempotencyKey": "dup-start"},
            ).json()["data"]
            second = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "我要退票", "idempotencyKey": "dup-start"},
            ).json()["data"]
            tasks = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/tasks").json()["data"]["list"]
            events = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/events").json()["data"]["list"]

        self.assertEqual(second, first)
        self.assertEqual([task["status"] for task in tasks], ["RUNNING"])
        self.assertEqual([task["currentStep"] for task in tasks], ["collect_order_no"])
        self.assertEqual([event["sequence"] for event in events], list(range(1, len(events) + 1)))
        self.assertEqual(
            [event["eventType"] for event in events],
            ["SESSION_CREATED", "USER_MESSAGE", "ROUTE_DECISION", "TASK_STARTED"],
        )
