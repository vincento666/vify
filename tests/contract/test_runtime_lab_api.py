import unittest

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import get_runtime_lab_service


class RuntimeLabApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_runtime_lab_service] = _fake_runtime_service

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_runtime_lab_service, None)

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

    def test_explicit_handoff_contract_preserves_active_task_and_events(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-lab/sessions")
            self.assertEqual(created.status_code, 200)
            session_id = created.json()["data"]["id"]

            started = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "我要退票", "idempotencyKey": "contract-handoff-start"},
            )
            handoff = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "我要人工客服", "idempotencyKey": "contract-handoff-request"},
            )
            events = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/events")

        self.assertEqual(started.status_code, 200)
        self.assertEqual(handoff.status_code, 200)
        started_data = started.json()["data"]
        handoff_data = handoff.json()["data"]
        decision = handoff_data["routeDecision"]
        self.assertEqual(decision["action"], "HANDOFF_TO_HUMAN")
        self.assertEqual(decision["handoff"]["sourceLayer"], "explicit_signal")
        self.assertEqual(decision["handoff"]["reasonCode"], "USER_REQUEST")
        self.assertEqual(decision["finalDecision"]["sourceLayer"], "explicit_signal")
        self.assertEqual(decision["finalDecision"]["reasonCode"], "USER_REQUEST")
        self.assertEqual(handoff_data["activeTask"]["id"], started_data["activeTask"]["id"])
        self.assertEqual(handoff_data["activeTask"]["sopId"], "refund_ticket")
        self.assertEqual(handoff_data["activeTask"]["currentStep"], started_data["activeTask"]["currentStep"])
        self.assertEqual(handoff_data["suspendedTasks"], [])

        event_list = events.json()["data"]["list"]
        event_types = [event["eventType"] for event in event_list]
        self.assertIn("HANDOFF_DECIDED", event_types)
        self.assertIn("HANDOFF_REQUESTED", event_types)
        requested = next(event for event in event_list if event["eventType"] == "HANDOFF_REQUESTED")
        snapshot = requested["payload"]["contextSnapshot"]
        self.assertEqual(snapshot["activeTaskSummary"]["sopId"], "refund_ticket")
        self.assertEqual(snapshot["routeEvidence"]["action"], "HANDOFF_TO_HUMAN")


def _fake_runtime_service(session: Session = Depends(get_session)) -> RuntimeLabService:
    return RuntimeLabService(RuntimeLabRepository(session))
