import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantCustomerBridgeApiContractTest(unittest.TestCase):
    _engine: Engine
    _factory: sessionmaker[Session]

    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_customer_bridge",
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

    def test_ai_assistant_can_call_read_only_customer_assistant_bridge_tool(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Bridge"}).json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "inspect customer assistant run",
                    "idempotencyKey": "customer-bridge-1",
                    "toolName": "customer_assistant_subagent_bridge",
                    "toolInput": {"sessionId": 9, "runId": 18, "message": "行李额度是多少"},
                },
            )
            run_id = message.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]

        output = message.json()["data"]["toolCalls"][0]["output"]
        self.assertEqual(message.status_code, 200, message.text)
        self.assertEqual(output["agentType"], "customer_assistant")
        self.assertEqual(output["subAgentRunId"], "customer-assistant-run-18")
        self.assertEqual(output["eventStreamRef"], "/api/v1/customer-assistant/sessions/9/events/stream?afterSequence=0")
        self.assertEqual(output["resultRef"], "/api/v1/customer-assistant/runs/18")
        self.assertFalse(output["workerAsyncRefs"]["supported"])
        self.assertIn("customer_assistant_subagent_bridge", [event["payload"].get("toolName") for event in events])

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
