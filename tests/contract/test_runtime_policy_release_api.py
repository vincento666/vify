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
from app.modules.runtime_policy.infra.schema import register_runtime_policy_tables
from tests.contract.test_runtime_policy_profile_api import _profile_payload


class RuntimePolicyReleaseApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "runtime_policy_release_api.db"
        self._engine = create_engine(f"sqlite:///{db_path}", future=True)
        register_runtime_policy_tables()
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

    def test_activate_is_blocked_before_required_gates_pass(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=_profile_payload("042.3 blocked"))
            profile_id = created.json()["data"]["id"]
            activated = client.post(
                f"/api/v1/runtime-policy/profiles/{profile_id}/activate",
                json={"activatedBy": "ops"},
            )

        self.assertEqual(activated.status_code, 400)
        self.assertIn("validation", activated.json()["message"])

    def test_profile_version_drift_invalidates_old_evaluation(self) -> None:
        with TestClient(app) as client:
            profile_id = _create_candidate_with_gates(client)
            approved = client.post(
                f"/api/v1/runtime-policy/profiles/{profile_id}/approve",
                json={"approvedBy": "ops"},
            )
            self.assertEqual(approved.status_code, 200)
            payload = _profile_payload("042.3 drifted")
            updated = client.put(f"/api/v1/runtime-policy/profiles/{profile_id}", json=payload)
            self.assertEqual(updated.status_code, 200)
            activated = client.post(
                f"/api/v1/runtime-policy/profiles/{profile_id}/activate",
                json={"activatedBy": "ops"},
            )

        self.assertEqual(activated.status_code, 400)
        self.assertIn("version", activated.json()["message"])

    def test_approve_canary_activate_records_release_and_switches_active_profile(self) -> None:
        with TestClient(app) as client:
            baseline = _profile_payload("042.3 baseline")
            baseline["status"] = "active"
            baseline_created = client.post("/api/v1/runtime-policy/profiles", json=baseline)
            baseline_id = baseline_created.json()["data"]["id"]
            profile_id = _create_candidate_with_gates(client, create_replay_source=False)
            approved = client.post(
                f"/api/v1/runtime-policy/profiles/{profile_id}/approve",
                json={"approvedBy": "ops"},
            )
            canary = client.post(
                f"/api/v1/runtime-policy/profiles/{profile_id}/canary",
                json={"canaryPercent": 25},
            )
            activated = client.post(
                f"/api/v1/runtime-policy/profiles/{profile_id}/activate",
                json={"activatedBy": "ops"},
            )
            releases = client.get("/api/v1/runtime-policy/releases", params={"profileId": profile_id})
            active_profile = client.get(f"/api/v1/runtime-policy/profiles/{profile_id}")
            archived_baseline = client.get(f"/api/v1/runtime-policy/profiles/{baseline_id}")

        self.assertEqual(approved.status_code, 200)
        self.assertEqual(canary.status_code, 200)
        self.assertEqual(activated.status_code, 200)
        self.assertEqual(approved.json()["data"]["status"], "approved")
        self.assertEqual(canary.json()["data"]["status"], "canary")
        self.assertEqual(canary.json()["data"]["canaryPercent"], 25)
        self.assertEqual(activated.json()["data"]["status"], "active")
        self.assertEqual(activated.json()["data"]["previousActiveProfileId"], baseline_id)
        self.assertEqual(releases.json()["data"]["total"], 1)
        self.assertEqual(active_profile.json()["data"]["status"], "active")
        self.assertEqual(archived_baseline.json()["data"]["status"], "archived")

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


def _create_candidate_with_gates(client: TestClient, *, create_replay_source: bool = True) -> int:
    candidate = _profile_payload("042.3 candidate")
    created = client.post("/api/v1/runtime-policy/profiles", json=candidate)
    profile_id = created.json()["data"]["id"]
    if create_replay_source:
        active = _profile_payload("042.3 replay source")
        active["status"] = "active"
        active["bindings"] = {**active["bindings"], "tenantId": "", "botId": "", "channel": "", "sopGroup": ""}
        client.post("/api/v1/runtime-policy/profiles", json=active)
    session = client.post("/api/v1/runtime-lab/sessions")
    session_id = session.json()["data"]["id"]
    client.post(
        f"/api/v1/runtime-lab/sessions/{session_id}/messages",
        json={"message": "机场附近打印店在哪里", "idempotencyKey": f"0423-{profile_id}"},
    )
    client.post(f"/api/v1/runtime-policy/profiles/{profile_id}/validate")
    client.post(f"/api/v1/runtime-policy/profiles/{profile_id}/replay/golden-matrix")
    client.post(
        f"/api/v1/runtime-policy/profiles/{profile_id}/replay/decision-logs",
        json={"sessionId": session_id, "action": "AGENT_FALLBACK"},
    )
    return int(profile_id)


if __name__ == "__main__":
    unittest.main()
