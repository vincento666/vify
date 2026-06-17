import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantKernelApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_api",
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

    def test_session_message_run_events_result_and_tools_contract(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Kernel contract"})
            session_id = created.json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={"message": "Echo this contract", "idempotencyKey": "contract-message-1"},
            )
            run_id = message.json()["data"]["runId"]
            run = client.get(f"/api/v1/ai-assistant/runs/{run_id}")
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events")
            result = client.get(f"/api/v1/ai-assistant/runs/{run_id}/result")
            tools = client.get("/api/v1/ai-assistant/tools")

        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["code"], 200)
        self.assertEqual(created.json()["data"]["status"], "ACTIVE")
        self.assertEqual(message.status_code, 200, message.text)
        self.assertEqual(message.json()["data"]["status"], "COMPLETED")
        self.assertEqual(message.json()["data"]["toolCalls"][0]["toolName"], "echo_context")
        self.assertIn("Echo this contract", message.json()["data"]["finalAnswer"])
        self.assertEqual(run.json()["data"]["id"], run_id)
        self.assertEqual(run.json()["data"]["status"], "COMPLETED")
        self.assertEqual([event["sequence"] for event in events.json()["data"]["list"]], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(events.json()["data"]["list"][0]["type"], "run.started")
        self.assertEqual(events.json()["data"]["list"][-1]["type"], "run.completed")
        self.assertEqual(result.json()["data"]["finalAnswer"], message.json()["data"]["finalAnswer"])
        self.assertEqual(tools.json()["data"]["list"][0]["name"], "echo_context")
        self.assertEqual(tools.json()["data"]["list"][0]["riskLevel"], "READ")

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
