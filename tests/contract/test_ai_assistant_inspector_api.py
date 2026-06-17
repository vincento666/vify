import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantInspectorApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_inspector",
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

    def test_run_inspector_exposes_tasks_tool_calls_approvals_errors_and_timeline(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Inspector"}).json()["data"][
                "id"
            ]
            first = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={"message": "echo inspector", "idempotencyKey": "inspector-echo"},
            )
            second = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "update customer profile",
                    "idempotencyKey": "inspector-waiting",
                    "toolName": "update_customer_profile",
                    "toolInput": {"customerId": "C-184"},
                },
            )
            runs = client.get(f"/api/v1/ai-assistant/sessions/{session_id}/runs")
            inspector = client.get(f"/api/v1/ai-assistant/runs/{second.json()['data']['runId']}/inspector")

        self.assertEqual(
            [run["id"] for run in runs.json()["data"]["list"]],
            [second.json()["data"]["runId"], first.json()["data"]["runId"]],
        )
        data = inspector.json()["data"]
        self.assertEqual(data["run"]["status"], "WAITING_APPROVAL")
        self.assertEqual(data["activeTasks"][0]["status"], "WAITING_APPROVAL")
        self.assertEqual(data["approvalQueue"][0]["riskLevel"], "BUSINESS_WRITE")
        self.assertEqual(data["toolCalls"], [])
        self.assertEqual(data["recentErrors"], [])
        self.assertEqual(
            [event["type"] for event in data["eventTimeline"]],
            [
                "run.started",
                "orchestration.phase_started",
                "model.call_completed",
                "approval.required",
                "proposed_action.created",
            ],
        )
        self.assertEqual(data["usage"]["inputTokens"], 0)

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
