import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantSessionLifecycleApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_session_lifecycle",
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

    def test_clear_history_and_delete_session_are_soft_deleted_from_public_contracts(self) -> None:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/ai-assistant/sessions",
                json={"title": "生命周期", "context": {"trace": "before-clear"}},
            )
            session_id = created.json()["data"]["id"]
            first = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={"message": "第一条消息", "idempotencyKey": "lifecycle-1"},
            )
            first_run_id = first.json()["data"]["runId"]

            cleared = client.delete(f"/api/v1/ai-assistant/sessions/{session_id}/history")
            runs_after_clear = client.get(f"/api/v1/ai-assistant/sessions/{session_id}/runs")
            session_after_clear = client.get(f"/api/v1/ai-assistant/sessions/{session_id}")
            first_run_after_clear = client.get(f"/api/v1/ai-assistant/runs/{first_run_id}")

            second = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={"message": "第二条消息", "idempotencyKey": "lifecycle-2"},
            )
            second_run_id = second.json()["data"]["runId"]
            deleted = client.delete(f"/api/v1/ai-assistant/sessions/{session_id}")
            listed = client.get("/api/v1/ai-assistant/sessions")
            deleted_session = client.get(f"/api/v1/ai-assistant/sessions/{session_id}")
            second_run_after_delete = client.get(f"/api/v1/ai-assistant/runs/{second_run_id}")

        self.assertEqual(cleared.status_code, 200, cleared.text)
        self.assertEqual(cleared.json()["data"], {"sessionId": session_id, "cleared": True})
        self.assertEqual(runs_after_clear.json()["data"], {"list": [], "total": 0})
        self.assertEqual(session_after_clear.json()["data"]["context"], {})
        self.assertEqual(first_run_after_clear.status_code, 404)

        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(deleted.json()["data"], {"sessionId": session_id, "deleted": True})
        self.assertNotIn(session_id, [session["id"] for session in listed.json()["data"]["list"]])
        self.assertEqual(deleted_session.status_code, 404)
        self.assertEqual(second_run_after_delete.status_code, 404)

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
