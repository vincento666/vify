import unittest

from fastapi.testclient import TestClient

from app.main import app


class RuntimeLabApiContractTest(unittest.TestCase):
    def test_create_message_tasks_and_events_contract(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-lab/sessions")
            self.assertEqual(created.status_code, 200)
            self.assertEqual(created.json()["code"], 200)
            session_id = created.json()["data"]["id"]

            message = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "我要退票", "idempotencyKey": "contract-start"},
            )
            self.assertEqual(message.status_code, 200)
            message_data = message.json()["data"]

            tasks = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/tasks")
            events = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/events")

        self.assertEqual(message_data["routeDecision"]["action"], "START_SOP")
        self.assertIn("reply", message_data)
        self.assertEqual(message_data["activeTask"]["sopId"], "refund_ticket")
        self.assertEqual(message_data["suspendedTasks"], [])
        self.assertIsNone(message_data["resumeOffer"])
        self.assertEqual(tasks.status_code, 200)
        self.assertEqual(tasks.json()["data"]["list"][0]["sopId"], "refund_ticket")
        self.assertEqual(events.status_code, 200)
        self.assertEqual(events.json()["data"]["list"][0]["eventType"], "SESSION_CREATED")
