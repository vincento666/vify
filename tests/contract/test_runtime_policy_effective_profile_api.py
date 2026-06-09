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


class RuntimePolicyEffectiveProfileApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "runtime_policy_effective.db"
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

    def test_effective_profile_resolves_active_binding_before_env_fallback(self) -> None:
        profile_payload = _profile_payload(name="041.2 active policy")
        profile_payload["status"] = "active"
        profile_payload["bindings"] = {
            **profile_payload["bindings"],
            "tenantId": "tenant-041",
            "botId": "bot-041",
            "channel": "web",
        }

        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=profile_payload)
            self.assertEqual(created.status_code, 200)

            matched = client.get(
                "/api/v1/runtime-policy/effective-profile",
                params={"tenantId": "tenant-041", "botId": "bot-041", "channel": "web"},
            )
            fallback = client.get(
                "/api/v1/runtime-policy/effective-profile",
                params={"tenantId": "another", "botId": "another", "channel": "app"},
            )

        self.assertEqual(matched.status_code, 200)
        matched_data = matched.json()["data"]
        self.assertEqual(matched_data["source"], "profile")
        self.assertEqual(matched_data["profileId"], created.json()["data"]["id"])
        self.assertEqual(matched_data["profileVersion"], 1)
        self.assertEqual(matched_data["policySnapshot"]["classifier"]["model"], "fake-runtime-classifier")

        self.assertEqual(fallback.status_code, 200)
        fallback_data = fallback.json()["data"]
        self.assertEqual(fallback_data["source"], "env")
        self.assertIsNone(fallback_data["profileId"])
        self.assertEqual(fallback_data["policySnapshot"]["classifier"]["mode"], "fake")

    def test_runtime_lab_config_uses_resolved_profile_sections_before_env_defaults(self) -> None:
        profile_payload = _profile_payload(name="041.2 runtime config policy")
        profile_payload["status"] = "active"
        profile_payload["bindings"] = {
            **profile_payload["bindings"],
            "tenantId": "tenant-runtime",
            "botId": "bot-runtime",
            "channel": "web",
        }
        profile_payload["classifier"] = {
            **profile_payload["classifier"],
            "model": "profile-classifier-model",
            "fallbackModel": "profile-fallback-model",
        }
        profile_payload["faq"] = {
            **profile_payload["faq"],
            "knowledgeBaseIds": [101, 102],
        }
        profile_payload["rag"] = {
            **profile_payload["rag"],
            "knowledgeBaseIds": [201],
        }

        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=profile_payload)
            self.assertEqual(created.status_code, 200)

            response = client.get(
                "/api/v1/runtime-lab/config",
                params={"tenantId": "tenant-runtime", "botId": "bot-runtime", "channel": "web"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["policyProfile"]["source"], "profile")
        self.assertEqual(data["policyProfile"]["profileId"], created.json()["data"]["id"])
        self.assertEqual(data["arbitrator"]["model"], "profile-classifier-model")
        self.assertEqual(data["arbitrator"]["fallbackModel"], "profile-fallback-model")
        self.assertEqual(data["faq"]["knowledgeBaseIds"], [101, 102])
        self.assertEqual(data["rag"]["knowledgeBaseIds"], [201])

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
