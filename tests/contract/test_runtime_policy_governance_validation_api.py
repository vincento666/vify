import tempfile
import unittest
from collections.abc import Generator
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.main import app
from app.modules.runtime_policy.infra.schema import register_runtime_policy_tables
from tests.contract.test_runtime_policy_profile_api import _profile_payload


class RuntimePolicyGovernanceValidationApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "runtime_policy_governance.db"
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

    def test_validate_malformed_profile_persists_failed_evaluation_run(self) -> None:
        payload = deepcopy(_profile_payload("042.1 malformed validation"))
        payload["thresholds"]["strongAcceptThreshold"] = 1.2
        payload["classifier"]["mode"] = "llm"
        payload["classifier"]["model"] = ""
        payload["fallbackAgent"]["allowedResponseTypes"] = ["answer", "teleport"]
        profile_id = self._insert_profile(payload)

        with TestClient(app) as client:
            validated = client.post(f"/api/v1/runtime-policy/profiles/{profile_id}/validate")
            listed = client.get(
                "/api/v1/runtime-policy/evaluation-runs",
                params={"profileId": profile_id, "runType": "validation"},
            )

        self.assertEqual(validated.status_code, 200)
        data = validated.json()["data"]
        self.assertEqual(data["profileId"], profile_id)
        self.assertEqual(data["runType"], "validation")
        self.assertEqual(data["status"], "failed")
        self.assertFalse(data["passed"])
        self.assertIn("thresholds.strongAcceptThreshold.out_of_range", data["failureReasons"])
        self.assertIn("classifier.model.required", data["failureReasons"])
        self.assertIn("fallbackAgent.allowedResponseTypes.unsupported", data["failureReasons"])
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 1)

    def test_validate_valid_profile_and_fetch_evaluation_run(self) -> None:
        payload = _profile_payload("042.1 valid validation")

        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=payload)
            profile_id = created.json()["data"]["id"]
            validated = client.post(f"/api/v1/runtime-policy/profiles/{profile_id}/validate")
            run_id = validated.json()["data"]["id"]
            fetched = client.get(f"/api/v1/runtime-policy/evaluation-runs/{run_id}")
            listed = client.get(
                "/api/v1/runtime-policy/evaluation-runs",
                params={"profileId": profile_id, "runType": "validation", "status": "passed"},
            )

        self.assertEqual(validated.status_code, 200)
        data = validated.json()["data"]
        self.assertEqual(data["status"], "passed")
        self.assertTrue(data["passed"])
        self.assertEqual(data["failureReasons"], [])
        self.assertEqual(data["guardrails"]["maxHandoffRateDelta"], 0.1)
        self.assertTrue(data["guardrails"]["requireGoldenMatrixPass"])
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["data"]["id"], run_id)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 1)

    def _insert_profile(self, payload: dict[str, object]) -> int:
        table = Base.metadata.tables["runtime_policy_profile"]
        now = datetime.now()
        with self._factory() as session:
            result = session.execute(
                table.insert()
                .values(
                    name=payload["name"],
                    description=payload["description"],
                    status=payload["status"],
                    version=1,
                    mode=payload["mode"],
                    bindings=payload["bindings"],
                    thresholds=payload["thresholds"],
                    classifier=payload["classifier"],
                    faq=payload["faq"],
                    rag=payload["rag"],
                    fallback_agent=payload["fallbackAgent"],
                    handoff=payload["handoff"],
                    audit=payload["audit"],
                    deleted=False,
                    created_at=now,
                    updated_at=now,
                )
                .returning(table.c.id)
            )
            profile_id = int(result.scalar_one())
            session.commit()
            return profile_id

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
