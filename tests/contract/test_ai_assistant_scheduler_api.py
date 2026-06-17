import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantSchedulerApiContractTest(unittest.TestCase):
    _engine: Engine
    _factory: sessionmaker[Session]

    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_scheduler_api",
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

    def test_multi_read_tool_request_records_parallel_batch_and_tool_calls(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Scheduler"}).json()["data"][
                "id"
            ]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "run two read tools",
                    "idempotencyKey": "scheduler-read-batch-1",
                    "toolCalls": [
                        {"toolName": "echo_context", "toolInput": {"message": "first read"}},
                        {"toolName": "echo_context", "toolInput": {"message": "second read"}},
                    ],
                },
            )
            run_id = message.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]

        data = message.json()["data"]
        self.assertEqual(message.status_code, 200, message.text)
        self.assertEqual([call["output"]["echo"] for call in data["toolCalls"]], ["first read", "second read"])
        batch_started = [event for event in events if event["type"] == "scheduler.batch_started"]
        self.assertEqual(len(batch_started), 1)
        self.assertEqual(batch_started[0]["payload"]["executionMode"], "READ_PARALLEL")
        self.assertEqual(batch_started[0]["payload"]["toolNames"], ["echo_context", "echo_context"])
        self.assertEqual(batch_started[0]["payload"]["readResources"], ["session:{}".format(session_id)])
        self.assertEqual(data["toolCalls"][0]["scheduler"]["lockMode"], "READ")
        self.assertEqual(data["toolCalls"][0]["scheduler"]["schedulerBatchId"], 1)
        self.assertIn("scheduler.batch_completed", [event["type"] for event in events])

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
