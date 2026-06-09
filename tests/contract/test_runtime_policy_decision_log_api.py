import tempfile
import unittest
from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.main import app
from tests.contract.test_runtime_policy_profile_api import _profile_payload


class RuntimePolicyDecisionLogApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "runtime_policy_decision_log.db"
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

    def test_runtime_message_persists_policy_snapshot_decision_log(self) -> None:
        profile_payload = _profile_payload("041.4 decision profile")
        profile_payload["status"] = "active"
        profile_payload["bindings"] = {
            **profile_payload["bindings"],
            "tenantId": "",
            "botId": "",
            "channel": "",
            "sopGroup": "",
        }

        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=profile_payload)
            self.assertEqual(created.status_code, 200)
            profile_id = created.json()["data"]["id"]
            session = client.post("/api/v1/runtime-lab/sessions")
            self.assertEqual(session.status_code, 200)
            session_id = session.json()["data"]["id"]
            message = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "机场附近打印店在哪里", "idempotencyKey": "decision-log"},
            )
            self.assertEqual(message.status_code, 200)
            logs = client.get(f"/api/v1/runtime-policy/sessions/{session_id}/decision-logs")

        self.assertEqual(logs.status_code, 200)
        data = logs.json()["data"]
        self.assertEqual(data["total"], 1)
        log = data["list"][0]
        self.assertEqual(log["sessionId"], session_id)
        self.assertEqual(log["policyProfileId"], profile_id)
        self.assertEqual(log["policyProfileVersion"], 1)
        self.assertEqual(log["policySnapshot"]["classifier"]["model"], "fake-runtime-classifier")
        self.assertEqual(log["finalAction"], message.json()["data"]["routeDecision"]["action"])
        self.assertIn("routeDecision", log["routeEvidence"])

    def test_decision_logs_filter_by_profile_action_source_and_time_range(self) -> None:
        profile_payload = _profile_payload("041.4 filter profile")
        profile_payload["status"] = "active"
        profile_payload["bindings"] = {
            **profile_payload["bindings"],
            "tenantId": "",
            "botId": "",
            "channel": "",
            "sopGroup": "",
        }

        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=profile_payload)
            self.assertEqual(created.status_code, 200)
            profile_id = created.json()["data"]["id"]
            session = client.post("/api/v1/runtime-lab/sessions")
            session_id = session.json()["data"]["id"]
            message = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "机场附近打印店在哪里", "idempotencyKey": "decision-filter"},
            )
            self.assertEqual(message.status_code, 200)
            all_logs = client.get("/api/v1/runtime-policy/decision-logs")
            created_at = all_logs.json()["data"]["list"][0]["createdAt"]
            created_from = (datetime.fromisoformat(created_at) - timedelta(seconds=1)).isoformat()
            created_to = (datetime.fromisoformat(created_at) + timedelta(seconds=1)).isoformat()
            filtered = client.get(
                "/api/v1/runtime-policy/decision-logs",
                params={
                    "sessionId": session_id,
                    "profileId": profile_id,
                    "action": "AGENT_FALLBACK",
                    "sourceLayer": "agent_policy",
                    "createdFrom": created_from,
                    "createdTo": created_to,
                },
            )
            empty = client.get(
                "/api/v1/runtime-policy/decision-logs",
                params={"action": "HANDOFF_TO_HUMAN"},
            )

        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.json()["data"]["total"], 1)
        log = filtered.json()["data"]["list"][0]
        self.assertEqual(log["sessionId"], session_id)
        self.assertEqual(log["policyProfileId"], profile_id)
        self.assertEqual(log["finalAction"], "AGENT_FALLBACK")
        self.assertEqual(log["sourceLayer"], "agent_policy")
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json()["data"]["total"], 0)

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
