import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.main import app
from app.modules.runtime_policy.infra.schema import register_runtime_policy_tables
from tests.contract.test_runtime_policy_profile_api import _profile_payload


class RuntimePolicyReleaseRollbackE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "runtime_policy_release_rollback_e2e.db"
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

    def test_operator_can_activate_then_rollback_audited_release(self) -> None:
        with TestClient(app) as client:
            baseline = _profile_payload("042.4 e2e baseline")
            baseline["status"] = "active"
            baseline_id = _post_profile(client, baseline)
            candidate_id = _create_candidate_with_gates(client)

            client.post(f"/api/v1/runtime-policy/profiles/{candidate_id}/approve", json={"approvedBy": "ops"})
            activated = client.post(
                f"/api/v1/runtime-policy/profiles/{candidate_id}/activate",
                json={"activatedBy": "ops"},
            )
            release_id = activated.json()["data"]["id"]
            rolled_back = client.post(
                f"/api/v1/runtime-policy/releases/{release_id}/rollback",
                json={"rolledBackBy": "ops", "reason": "failed canary observation"},
            )
            detail = client.get(f"/api/v1/runtime-policy/releases/{release_id}")
            restored_baseline = client.get(f"/api/v1/runtime-policy/profiles/{baseline_id}")
            archived_candidate = client.get(f"/api/v1/runtime-policy/profiles/{candidate_id}")

        self.assertEqual(activated.status_code, 200)
        self.assertEqual(rolled_back.status_code, 200)
        self.assertEqual(rolled_back.json()["data"]["status"], "rolled_back")
        self.assertEqual(restored_baseline.json()["data"]["status"], "active")
        self.assertEqual(archived_candidate.json()["data"]["status"], "archived")
        self.assertEqual(
            [event["eventType"] for event in detail.json()["data"]["auditEvents"]],
            ["release_approved", "release_activated", "release_rolled_back"],
        )

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


def _create_candidate_with_gates(client: TestClient) -> int:
    profile_id = _post_profile(client, _profile_payload("042.4 e2e candidate"))
    session = client.post("/api/v1/runtime-lab/sessions")
    session_id = session.json()["data"]["id"]
    client.post(
        f"/api/v1/runtime-lab/sessions/{session_id}/messages",
        json={"message": "机场附近打印店在哪里", "idempotencyKey": f"0424-e2e-{profile_id}"},
    )
    client.post(f"/api/v1/runtime-policy/profiles/{profile_id}/validate")
    client.post(f"/api/v1/runtime-policy/profiles/{profile_id}/replay/golden-matrix")
    client.post(
        f"/api/v1/runtime-policy/profiles/{profile_id}/replay/decision-logs",
        json={"sessionId": session_id, "action": "AGENT_FALLBACK"},
    )
    return profile_id


def _post_profile(client: TestClient, payload: dict[str, Any]) -> int:
    response = client.post("/api/v1/runtime-policy/profiles", json=payload)
    assert response.status_code == 200, response.text
    return int(response.json()["data"]["id"])


if __name__ == "__main__":
    unittest.main()
