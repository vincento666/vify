import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantKernelE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_e2e",
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

    def test_one_message_to_read_only_tool_to_final_result_replay(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "E2E"})
            session_id = created.json()["data"]["id"]
            first = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={"message": "Please echo the visible execution.", "idempotencyKey": "e2e-message-1"},
            )
            replay = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={"message": "Please echo the visible execution.", "idempotencyKey": "e2e-message-1"},
            )
            run_id = first.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events")

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["data"]["replayed"], False)
        self.assertEqual(replay.json()["data"]["runId"], run_id)
        self.assertEqual(replay.json()["data"]["replayed"], True)
        self.assertEqual(first.json()["data"]["planningStrategy"], "auto_lightweight")
        self.assertEqual(first.json()["data"]["plan"]["id"], f"plan-{run_id}")
        self.assertEqual(first.json()["data"]["toolCalls"][0]["status"], "COMPLETED")
        self.assertEqual(first.json()["data"]["toolCalls"][0]["output"]["echo"], "Please echo the visible execution.")
        event_types = [event["type"] for event in events.json()["data"]["list"]]
        self.assertIn("plan.created", event_types)
        self.assertIn("task.created", event_types)
        self.assertIn("plan.step_started", event_types)
        self.assertIn("task.updated", event_types)
        self.assertIn("tool.call_started", event_types)
        self.assertIn("tool.call_completed", event_types)
        self.assertIn("plan.step_completed", event_types)
        self.assertIn("task.completed", event_types)
        self.assertLess(event_types.index("plan.created"), event_types.index("tool.call_started"))
        self.assertLess(event_types.index("tool.call_completed"), event_types.index("task.completed"))

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
