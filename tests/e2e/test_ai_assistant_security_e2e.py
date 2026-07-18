import unittest
from collections.abc import Generator
import os
import tempfile
from pathlib import Path

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
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._previous_workspace_root = os.environ.get("HIFY_WORKSPACE_ROOT")
        os.environ["HIFY_WORKSPACE_ROOT"] = self._tmp_dir.name
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            ai_assistant_tool_profile="demo",
        )

    def tearDown(self) -> None:
        if self._previous_workspace_root is None:
            os.environ.pop("HIFY_WORKSPACE_ROOT", None)
        else:
            os.environ["HIFY_WORKSPACE_ROOT"] = self._previous_workspace_root
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
        self.assertEqual(message.json()["data"]["planningStrategy"], "auto_lightweight")
        self.assertEqual(message.json()["data"]["plan"]["status"], "BLOCKED")
        self.assertEqual(denied.json()["data"]["status"], "DENIED")
        event_types = [event["type"] for event in events.json()["data"]["list"]]
        self.assertIn("plan.created", event_types)
        self.assertIn("task.created", event_types)
        self.assertIn("approval.required", event_types)
        self.assertIn("plan.blocked", event_types)
        self.assertIn("task.blocked", event_types)
        self.assertIn("proposed_action.created", event_types)
        self.assertIn("approval.denied", event_types)
        self.assertLess(event_types.index("plan.created"), event_types.index("approval.required"))
        self.assertLess(event_types.index("approval.required"), event_types.index("approval.denied"))

    def test_always_approve_workspace_write_still_emits_safety_and_lock_evidence(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Security E2E"}).json()[
                "data"
            ]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "write safely",
                    "idempotencyKey": "security-e2e-gated-write",
                    "approvalMode": "always_approve",
                    "toolName": "write_workspace_file",
                    "toolInput": {"path": "safe-e2e.txt", "content": "safe e2e"},
                },
            )
            run_id = message.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]
            run = client.get(f"/api/v1/ai-assistant/runs/{run_id}").json()["data"]

        event_types = [event["type"] for event in events]
        self.assertEqual(message.json()["data"]["status"], "COMPLETED")
        self.assertEqual((Path(self._tmp_dir.name) / "safe-e2e.txt").read_text(encoding="utf-8"), "safe e2e")
        self.assertIn("permission.evaluated", event_types)
        self.assertIn("sandbox.evaluated", event_types)
        self.assertIn("resource_lock.acquired", event_types)
        self.assertIn("resource_lock.released", event_types)
        self.assertEqual(run["result"]["toolCalls"][0]["output"]["lock"]["scope"], "db")

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
