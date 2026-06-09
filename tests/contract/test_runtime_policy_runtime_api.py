import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.main import app
from tests.contract.test_runtime_policy_profile_api import _profile_payload


class RuntimePolicyRuntimeApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "runtime_policy_runtime.db"
        self._engine = create_engine(f"sqlite:///{db_path}", future=True)
        Base.metadata.create_all(bind=self._engine)
        self._factory = sessionmaker(
            bind=self._engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_runtime_message_disables_fallback_agent_from_active_profile(self) -> None:
        profile_payload = _profile_payload("041.3 disabled fallback")
        profile_payload["status"] = "active"
        profile_payload["bindings"] = {
            **profile_payload["bindings"],
            "tenantId": "",
            "botId": "",
            "channel": "",
            "sopGroup": "",
        }
        profile_payload["fallbackAgent"] = {
            **profile_payload["fallbackAgent"],
            "enabled": False,
        }

        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=profile_payload)
            self.assertEqual(created.status_code, 200)
            session = client.post("/api/v1/runtime-lab/sessions")
            self.assertEqual(session.status_code, 200)
            session_id = session.json()["data"]["id"]
            message = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "机场附近打印店在哪里", "idempotencyKey": "disabled-fallback"},
            )

        self.assertEqual(message.status_code, 200)
        decision = message.json()["data"]["routeDecision"]
        self.assertEqual(decision["action"], "CLARIFY")
        self.assertIsNone(decision["agentAnswer"])

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
