import json
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


class CustomerAssistantWorkerProfileApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "customer_assistant_worker_profiles.db"
        self._engine = create_engine(f"sqlite:///{db_path}", future=True)
        Base.metadata.create_all(bind=self._engine)
        self._factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, expire_on_commit=False)
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(
            runtime_lab_sop_chatflow_ids=None,
            customer_assistant_worker_profiles_json=json.dumps(
                {
                    "profiles": [
                        {
                            "profileId": "configured_refund_stub",
                            "taskKey": "refund_ticket",
                            "taskType": "QA",
                            "workerType": "stub_qa",
                            "workerRef": "configured_refund_stub",
                            "modelPolicyRef": "demo-model",
                            "promptRef": "demo-refund-prompt",
                            "toolRefs": ["lookup_order"],
                            "riskPolicyRef": "manual_confirm",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
        )

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_exposes_profiles_and_routes_tasks_from_override(self) -> None:
        with TestClient(app) as client:
            profiles = client.get("/api/v1/customer-assistant/worker-profiles")
            self.assertEqual(profiles.status_code, 200, profiles.text)
            profile_data = profiles.json()["data"]
            self.assertEqual(profile_data["total"], 1)
            self.assertEqual(profile_data["list"][0]["workerRef"], "configured_refund_stub")
            self.assertEqual(profile_data["list"][0]["modelPolicyRef"], "demo-model")

            created = client.post("/api/v1/customer-assistant/sessions", json={"context": {}})
            session_id = int(created.json()["data"]["id"])
            turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "configured-refund"},
            )
            self.assertEqual(turn.status_code, 200, turn.text)
            tasks = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/tasks").json()["data"]["list"]

        self.assertEqual(tasks[0]["taskType"], "QA")
        self.assertEqual(tasks[0]["workerType"], "stub_qa")
        self.assertEqual(tasks[0]["workerRef"], "configured_refund_stub")

    def test_task_events_expose_profile_refs_for_eval_observability(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/customer-assistant/sessions", json={"context": {}})
            session_id = int(created.json()["data"]["id"])
            turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "profile-refs"},
            )
            self.assertEqual(turn.status_code, 200, turn.text)
            events = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/events").json()["data"]["list"]

        task_started = next(event for event in events if event["type"] == "task_started")
        self.assertEqual(task_started["payload"]["profileRefs"]["profileId"], "configured_refund_stub")
        self.assertEqual(task_started["payload"]["profileRefs"]["modelPolicyRef"], "demo-model")
        self.assertEqual(task_started["payload"]["profileRefs"]["riskPolicyRef"], "manual_confirm")
        self.assertEqual(task_started["observability"]["profileRefs"]["profileId"], "configured_refund_stub")

    def test_task_recognized_records_profile_refs_for_operator_evidence(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/customer-assistant/sessions", json={"context": {}})
            session_id = int(created.json()["data"]["id"])
            turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "recognition-profile-refs"},
            )
            self.assertEqual(turn.status_code, 200, turn.text)
            events = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/events").json()["data"]["list"]

        task_recognized = next(event for event in events if event["type"] == "task_recognized")
        command = task_recognized["payload"]["commands"][0]
        self.assertEqual(command["taskKey"], "refund_ticket")
        self.assertEqual(command["profileRefs"]["profileId"], "configured_refund_stub")
        self.assertEqual(command["profileRefs"]["modelPolicyRef"], "demo-model")
        self.assertEqual(command["profileRefs"]["promptRef"], "demo-refund-prompt")
        self.assertEqual(command["profileRefs"]["toolRefs"], ["lookup_order"])
        self.assertEqual(command["profileRefs"]["riskPolicyRef"], "manual_confirm")

    def test_persisted_profile_override_updates_catalog_and_routing(self) -> None:
        payload = {
            "taskKey": "refund_ticket",
            "taskType": "REFUND",
            "workerType": "chatflow_sop",
            "workerRef": "runtime_configured_refund",
            "modelPolicyRef": "demo-model-v2",
            "promptRef": "runtime-refund-prompt",
            "toolRefs": ["lookup_order", "refund_policy_lookup"],
            "riskPolicyRef": "manual_confirm_high_risk",
            "enabled": True,
        }

        with TestClient(app) as client:
            patched = client.patch(
                "/api/v1/customer-assistant/worker-profiles/configured_refund_stub",
                json=payload,
            )
            self.assertEqual(patched.status_code, 200, patched.text)
            self.assertEqual(patched.json()["data"]["workerRef"], "runtime_configured_refund")

            profiles = client.get("/api/v1/customer-assistant/worker-profiles").json()["data"]["list"]
            profile = next(item for item in profiles if item["profileId"] == "configured_refund_stub")
            self.assertEqual(profile["modelPolicyRef"], "demo-model-v2")
            self.assertEqual(profile["toolRefs"], ["lookup_order", "refund_policy_lookup"])

            created = client.post("/api/v1/customer-assistant/sessions", json={"context": {}})
            session_id = int(created.json()["data"]["id"])
            turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "configured-refund-v2"},
            )
            self.assertEqual(turn.status_code, 200, turn.text)
            tasks = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/tasks").json()["data"]["list"]
            events = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/events").json()["data"]["list"]

        self.assertEqual(tasks[0]["workerRef"], "runtime_configured_refund")
        task_recognized = next(event for event in events if event["type"] == "task_recognized")
        profile_refs = task_recognized["payload"]["commands"][0]["profileRefs"]
        self.assertEqual(profile_refs["profileId"], "configured_refund_stub")
        self.assertEqual(profile_refs["modelPolicyRef"], "demo-model-v2")
        self.assertEqual(profile_refs["promptRef"], "runtime-refund-prompt")
        self.assertEqual(profile_refs["riskPolicyRef"], "manual_confirm_high_risk")

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session
