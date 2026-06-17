import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database
from tests.contract.test_runtime_policy_profile_api import _profile_payload


class RuntimePolicyRuntimeApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(self, "runtime_policy_runtime")
        self._engine = self._database.engine
        self._factory = self._database.session_factory
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

    def test_runtime_message_uses_profile_classifier_threshold(self) -> None:
        profile_payload = _profile_payload("041.R1 strict threshold")
        profile_payload["status"] = "active"
        profile_payload["bindings"] = {
            **profile_payload["bindings"],
            "tenantId": "",
            "botId": "",
            "channel": "",
            "sopGroup": "",
        }
        profile_payload["thresholds"] = {
            **profile_payload["thresholds"],
            "classifierMinConfidence": 0.99,
        }

        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=profile_payload)
            self.assertEqual(created.status_code, 200)
            session = client.post("/api/v1/runtime-lab/sessions")
            session_id = session.json()["data"]["id"]
            message = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "我要订广州飞北京的航班", "idempotencyKey": "strict-threshold"},
            )

        self.assertEqual(message.status_code, 200)
        decision = message.json()["data"]["routeDecision"]
        self.assertEqual(decision["action"], "CLARIFY")
        self.assertEqual(decision["classifierRequest"]["thresholds"]["classifierMinConfidence"], 0.99)

    def test_runtime_message_uses_profile_faq_switch(self) -> None:
        profile_payload = _profile_payload("041.R1 faq disabled")
        profile_payload["status"] = "active"
        profile_payload["bindings"] = {
            **profile_payload["bindings"],
            "tenantId": "",
            "botId": "",
            "channel": "",
            "sopGroup": "",
        }
        profile_payload["faq"] = {
            **profile_payload["faq"],
            "exactEnabled": False,
            "semanticEnabled": False,
            "knowledgeBaseIds": [],
        }

        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=profile_payload)
            self.assertEqual(created.status_code, 200)
            session = client.post("/api/v1/runtime-lab/sessions")
            session_id = session.json()["data"]["id"]
            message = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "儿童票可以退吗", "idempotencyKey": "faq-disabled"},
            )

        self.assertEqual(message.status_code, 200)
        decision = message.json()["data"]["routeDecision"]
        candidate_types = {candidate["candidate_type"] for candidate in decision["candidates"]}
        self.assertNotIn("ANSWER_FAQ", candidate_types)
        self.assertNotEqual(decision["action"], "ANSWER_FAQ")

    def test_runtime_message_uses_profile_candidate_top_k(self) -> None:
        profile_payload = _profile_payload("041.R1 candidate top k")
        profile_payload["status"] = "active"
        profile_payload["bindings"] = {
            **profile_payload["bindings"],
            "tenantId": "",
            "botId": "",
            "channel": "",
            "sopGroup": "",
        }
        profile_payload["thresholds"] = {
            **profile_payload["thresholds"],
            "candidateTopK": 1,
        }

        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=profile_payload)
            self.assertEqual(created.status_code, 200)
            session = client.post("/api/v1/runtime-lab/sessions")
            session_id = session.json()["data"]["id"]
            message = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "我要退票，也想改签", "idempotencyKey": "candidate-top-k"},
            )

        self.assertEqual(message.status_code, 200)
        decision = message.json()["data"]["routeDecision"]
        self.assertLessEqual(len(decision["classifierRequest"]["candidates"]), 1)

    def test_runtime_message_uses_profile_candidate_source_weights(self) -> None:
        profile_payload = _profile_payload("041.R1 candidate source weights")
        profile_payload["status"] = "active"
        profile_payload["bindings"] = {
            **profile_payload["bindings"],
            "tenantId": "",
            "botId": "",
            "channel": "",
            "sopGroup": "",
        }
        profile_payload["thresholds"] = {
            **profile_payload["thresholds"],
            "candidateTopK": 1,
            "candidateSourceWeights": {
                "explicit_signal": 0.1,
                "mock_semantic_recall": 2.0,
            },
        }

        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=profile_payload)
            self.assertEqual(created.status_code, 200)
            session = client.post("/api/v1/runtime-lab/sessions")
            session_id = session.json()["data"]["id"]
            message = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "我要退票，也想改签", "idempotencyKey": "candidate-source-weights"},
            )

        self.assertEqual(message.status_code, 200)
        decision = message.json()["data"]["routeDecision"]
        self.assertEqual(len(decision["candidates"]), 1)
        self.assertEqual(decision["candidates"][0]["source"], "mock_semantic_recall")
        self.assertEqual(decision["candidates"][0]["payload"]["policyWeight"]["sourceWeight"], 2.0)

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
