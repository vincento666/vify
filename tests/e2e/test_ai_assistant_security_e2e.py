import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantSecurityE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_security_e2e",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_high_risk_action_can_be_denied_and_replayed(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Security E2E"}).json()[
                "data"
            ]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "update customer profile",
                    "idempotencyKey": "security-e2e-deny",
                    "approvalMode": "smart_approval",
                    "toolName": "update_customer_profile",
                    "toolInput": {"customerId": "C-9", "field": "tier", "value": "gold"},
                },
            )
            approval_id = message.json()["data"]["approvalId"]
            denied = client.post(
                f"/api/v1/ai-assistant/approvals/{approval_id}/deny",
                json={"actorId": "operator-e2e", "reason": "needs review"},
            )
            events = client.get(f"/api/v1/ai-assistant/runs/{message.json()['data']['runId']}/events")

        self.assertEqual(message.json()["data"]["status"], "WAITING_APPROVAL")
        self.assertEqual(denied.json()["data"]["status"], "DENIED")
        self.assertEqual(
            [event["type"] for event in events.json()["data"]["list"]],
            [
                "run.started",
                "orchestration.phase_started",
                "model.call_completed",
                "approval.required",
                "proposed_action.created",
                "approval.denied",
            ],
        )

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
