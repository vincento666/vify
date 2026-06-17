import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database
from app.modules.runtime_policy.infra.schema import register_runtime_policy_tables
from tests.contract.test_runtime_policy_profile_api import _profile_payload


class RuntimePolicyReplayApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(self, "runtime_policy_replay", register=register_runtime_policy_tables)
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_golden_matrix_replay_persists_expected_vs_actual_run(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=_profile_payload("042.2 golden profile"))
            profile_id = created.json()["data"]["id"]
            replayed = client.post(f"/api/v1/runtime-policy/profiles/{profile_id}/replay/golden-matrix")
            listed = client.get(
                "/api/v1/runtime-policy/evaluation-runs",
                params={"profileId": profile_id, "runType": "golden_matrix", "status": "passed"},
            )

        self.assertEqual(replayed.status_code, 200)
        data = replayed.json()["data"]
        self.assertEqual(data["runType"], "golden_matrix")
        self.assertEqual(data["status"], "passed")
        self.assertTrue(data["passed"])
        self.assertGreaterEqual(data["result"]["caseCount"], 4)
        self.assertEqual(data["result"]["failedCount"], 0)
        self.assertIn("expected", data["result"]["cases"][0])
        self.assertIn("actual", data["result"]["cases"][0])
        self.assertEqual(data["riskDeltas"]["unsupportedActionCount"], 0)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 1)

    def test_decision_log_replay_filters_logs_and_persists_risk_deltas(self) -> None:
        payload = _profile_payload("042.2 decision replay profile")
        payload["status"] = "active"
        payload["bindings"] = {
            **payload["bindings"],
            "tenantId": "",
            "botId": "",
            "channel": "",
            "sopGroup": "",
        }

        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=payload)
            profile_id = created.json()["data"]["id"]
            session = client.post("/api/v1/runtime-lab/sessions")
            session_id = session.json()["data"]["id"]
            message = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "机场附近打印店在哪里", "idempotencyKey": "0422-replay"},
            )
            self.assertEqual(message.status_code, 200)
            replayed = client.post(
                f"/api/v1/runtime-policy/profiles/{profile_id}/replay/decision-logs",
                json={"sessionId": session_id, "action": "AGENT_FALLBACK"},
            )
            listed = client.get(
                "/api/v1/runtime-policy/evaluation-runs",
                params={"profileId": profile_id, "runType": "decision_log_replay"},
            )

        self.assertEqual(replayed.status_code, 200)
        data = replayed.json()["data"]
        self.assertEqual(data["runType"], "decision_log_replay")
        self.assertEqual(data["status"], "passed")
        self.assertTrue(data["passed"])
        self.assertEqual(data["result"]["logCount"], 1)
        self.assertEqual(data["result"]["changedDecisionCount"], 0)
        self.assertEqual(data["riskDeltas"]["handoffRateDelta"], 0.0)
        self.assertEqual(data["riskDeltas"]["clarificationRateDelta"], 0.0)
        self.assertEqual(data["riskDeltas"]["unsupportedActionCount"], 0)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 1)

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
