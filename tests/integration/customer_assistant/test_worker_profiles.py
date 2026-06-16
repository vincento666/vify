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


def _host_headers(tenant_id: str, org_id: str | None = None) -> dict[str, str]:
    return {
        "X-Hify-Actor-Id": f"operator-{tenant_id}",
        "X-Hify-Actor-Name": f"Operator {tenant_id}",
        "X-Hify-Tenant-Id": tenant_id,
        "X-Hify-Org-Id": org_id or tenant_id,
        "X-Hify-Source": "embedded-demo-shell",
        "X-Hify-Permissions": "customer_assistant:read,customer_assistant:operate",
        "X-Request-Id": f"req-{tenant_id}",
    }


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

    def test_worker_profile_overrides_are_scoped_by_host_tenant(self) -> None:
        tenant_a_headers = _host_headers("tenant-profile-a")
        tenant_b_headers = _host_headers("tenant-profile-b")
        payload = {
            "taskKey": "refund_ticket",
            "taskType": "REFUND",
            "workerType": "chatflow_sop",
            "workerRef": "tenant_a_refund_worker",
            "modelPolicyRef": "tenant-a-model",
            "promptRef": "tenant-a-prompt",
            "toolRefs": ["lookup_order"],
            "riskPolicyRef": "manual_confirm_high_risk",
            "enabled": True,
        }

        with TestClient(app) as client:
            patched = client.patch(
                "/api/v1/customer-assistant/worker-profiles/configured_refund_stub",
                json=payload,
                headers=tenant_a_headers,
            )
            self.assertEqual(patched.status_code, 200, patched.text)

            tenant_a_profile = client.get(
                "/api/v1/customer-assistant/worker-profiles",
                headers=tenant_a_headers,
            ).json()["data"]["list"][0]
            tenant_b_profile = client.get(
                "/api/v1/customer-assistant/worker-profiles",
                headers=tenant_b_headers,
            ).json()["data"]["list"][0]

            created_b = client.post(
                "/api/v1/customer-assistant/sessions",
                json={"context": {}},
                headers=tenant_b_headers,
            )
            session_b = int(created_b.json()["data"]["id"])
            turn_b = client.post(
                f"/api/v1/customer-assistant/sessions/{session_b}/turns",
                json={"message": "我要退票", "idempotencyKey": "tenant-b-refund"},
                headers=tenant_b_headers,
            )
            self.assertEqual(turn_b.status_code, 200, turn_b.text)
            task_b = client.get(
                f"/api/v1/customer-assistant/sessions/{session_b}/tasks",
                headers=tenant_b_headers,
            ).json()["data"]["list"][0]

        self.assertEqual(tenant_a_profile["workerRef"], "tenant_a_refund_worker")
        self.assertEqual(tenant_b_profile["workerRef"], "configured_refund_stub")
        self.assertEqual(task_b["workerRef"], "configured_refund_stub")

    def test_disabled_worker_profile_override_falls_back_to_configured_profile(self) -> None:
        payload = {
            "taskKey": "refund_ticket",
            "taskType": "REFUND",
            "workerType": "chatflow_sop",
            "workerRef": "disabled_refund_worker",
            "modelPolicyRef": "disabled-model",
            "promptRef": "disabled-prompt",
            "toolRefs": ["lookup_order"],
            "riskPolicyRef": "manual_confirm_high_risk",
            "enabled": False,
        }

        with TestClient(app) as client:
            patched = client.patch(
                "/api/v1/customer-assistant/worker-profiles/configured_refund_stub",
                json=payload,
            )
            self.assertEqual(patched.status_code, 200, patched.text)
            profiles = client.get("/api/v1/customer-assistant/worker-profiles").json()["data"]["list"]
            created = client.post("/api/v1/customer-assistant/sessions", json={"context": {}})
            session_id = int(created.json()["data"]["id"])
            turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "disabled-profile-fallback"},
            )
            self.assertEqual(turn.status_code, 200, turn.text)
            task = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/tasks").json()["data"]["list"][0]

        self.assertEqual(profiles[0]["workerRef"], "configured_refund_stub")
        self.assertEqual(profiles[0]["modelPolicyRef"], "demo-model")
        self.assertEqual(task["workerRef"], "configured_refund_stub")

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session
