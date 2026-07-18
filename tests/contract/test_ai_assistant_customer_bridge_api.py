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

    def test_persisted_child_execution_adapter_is_registered_by_composition_root(
        self,
    ) -> None:
        with TestClient(app) as client:
            tools = client.get("/api/v1/ai-assistant/tools")

        self.assertEqual(tools.status_code, 200, tools.text)
        self.assertIn(
            "customer_assistant_subagent_bridge",
            [tool["name"] for tool in tools.json()["data"]["list"]],
        )

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
