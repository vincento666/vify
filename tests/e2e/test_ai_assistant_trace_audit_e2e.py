import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantTraceAuditE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_trace_audit_e2e",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            ai_assistant_tool_profile="demo",
        )

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()

    def test_completed_run_exports_auditable_trace_eval_and_budget_snapshot(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Trace Audit E2E"}).json()[
                "data"
            ]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "trace this deterministic run",
                    "idempotencyKey": "trace-audit-e2e",
                    "approvalMode": "always_approve",
                    "toolName": "echo_context",
                    "aiAssistantBudget": {"maxUsd": 0.000001},
                    "modelBudgetPolicy": {"primaryModel": "qwen-max", "fallbackModel": "qwen-turbo"},
                },
            ).json()["data"]
            audit = client.get(f"/api/v1/ai-assistant/runs/{turn['runId']}/audit")

        self.assertEqual(audit.status_code, 200, audit.text)
        data = audit.json()["data"]
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["audit"]["prompt"]["message"], "trace this deterministic run")
        self.assertEqual(data["audit"]["plan"]["planningStrategy"], "auto_lightweight")
        self.assertEqual(data["audit"]["toolCalls"][0]["toolName"], "echo_context")
        self.assertTrue(data["audit"]["finalResult"])
        self.assertIn("context", data["budget"])
        self.assertIn("token", data["budget"])
        self.assertEqual(data["budget"]["policy"]["status"], "over_budget")
        self.assertEqual(data["budget"]["policy"]["model"]["action"], "degrade")
        self.assertEqual(data["budget"]["policy"]["model"]["selectedModel"], "qwen-turbo")
        self.assertFalse(data["eval"]["passed"])
        self.assertGreaterEqual(len(data["trace"]["spans"]), 5)

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
