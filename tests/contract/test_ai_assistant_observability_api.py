import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantObservabilityApiContractTest(unittest.TestCase):
    _engine: Engine
    _factory: sessionmaker[Session]

    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_observability",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        if self._database.engine is None or self._database.session_factory is None:
            raise RuntimeError("MySQL8 test database was not initialised")
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings()

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()

    def test_inspector_exposes_observability_and_benchmark_snapshot(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Observability"}).json()["data"][
                "id"
            ]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={"message": "observe this run", "idempotencyKey": "observability-1"},
            ).json()["data"]
            inspector = client.get(f"/api/v1/ai-assistant/runs/{turn['runId']}/inspector").json()["data"]

        observability = inspector["observability"]
        self.assertEqual(observability["runId"], turn["runId"])
        self.assertEqual(observability["status"], "COMPLETED")
        self.assertGreaterEqual(observability["eventCount"], 7)
        self.assertEqual(observability["toolCallCount"], 1)
        self.assertEqual(observability["benchmark"]["name"], "ai_assistant_deterministic_mvp")
        self.assertTrue(observability["benchmark"]["passed"])
        event_types = [event["type"] for event in inspector["eventTimeline"]]
        self.assertIn("permission.evaluated", event_types)
        self.assertIn("sandbox.evaluated", event_types)
        self.assertIn("resource_lock.acquired", event_types)

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
