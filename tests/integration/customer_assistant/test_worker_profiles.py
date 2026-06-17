import json
import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


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
        self._database = mysql8_unittest_database(self, "customer_assistant_worker_profiles")
        self._engine = self._database.engine
        self._factory = self._database.session_factory
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

    def test_invalid_worker_profile_update_is_rejected_without_persisting_override(self) -> None:
        valid_payload = {
            "taskKey": "refund_ticket",
            "taskType": "REFUND",
            "workerType": "chatflow_sop",
            "workerRef": "runtime_configured_refund",
            "modelPolicyRef": "demo-model-v2",
            "promptRef": "runtime-refund-prompt",
            "toolRefs": ["lookup_order", "refund_policy_lookup"],
            "toolPolicyRef": "strict-read-before-write",
            "riskPolicyRef": "manual_confirm_high_risk",
            "outputSchemaRef": "refund_worker_result_v2",
            "enabled": True,
        }
        invalid_cases = [
            ({"workerType": "raect_worker"}, "Supported worker types"),
            ({"modelPolicyRef": ""}, "modelPolicyRef"),
            ({"promptRef": " "}, "promptRef"),
            ({"toolPolicyRef": ""}, "toolPolicyRef"),
            ({"riskPolicyRef": ""}, "riskPolicyRef"),
            ({"outputSchemaRef": ""}, "outputSchemaRef"),
            ({"toolRefs": ["lookup_order", "", "lookup_order"]}, "toolRefs"),
        ]

        with TestClient(app) as client:
            baseline = client.get("/api/v1/customer-assistant/worker-profiles").json()["data"]["list"][0]

            for override, expected_message in invalid_cases:
                with self.subTest(override=override):
                    rejected = client.patch(
                        "/api/v1/customer-assistant/worker-profiles/configured_refund_stub",
                        json={**valid_payload, **override},
                    )
                    self.assertEqual(rejected.status_code, 400, rejected.text)
                    self.assertIn(expected_message, rejected.json()["message"])

                    profiles = client.get("/api/v1/customer-assistant/worker-profiles").json()["data"]["list"]
                    profile = next(item for item in profiles if item["profileId"] == "configured_refund_stub")
                    self.assertEqual(profile["workerType"], baseline["workerType"])
                    self.assertEqual(profile["workerRef"], baseline["workerRef"])
                    self.assertEqual(profile["modelPolicyRef"], baseline["modelPolicyRef"])
                    self.assertEqual(profile["promptRef"], baseline["promptRef"])
                    self.assertEqual(profile["toolRefs"], baseline["toolRefs"])
                    self.assertEqual(profile["toolPolicyRef"], baseline["toolPolicyRef"])
                    self.assertEqual(profile["riskPolicyRef"], baseline["riskPolicyRef"])
                    self.assertEqual(profile["outputSchemaRef"], baseline["outputSchemaRef"])

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

    def test_react_worker_profile_tool_refs_constrain_runtime_policy(self) -> None:
        payload = {
            "taskKey": "refund_ticket",
            "taskType": "REFUND",
            "workerType": "react_worker",
            "workerRef": "configured_refund_react",
            "modelPolicyRef": "demo-react-model",
            "promptRef": "demo-react-prompt",
            "toolRefs": [],
            "riskPolicyRef": "manual_confirm_high_risk",
            "enabled": True,
        }

        with TestClient(app) as client:
            patched = client.patch(
                "/api/v1/customer-assistant/worker-profiles/configured_refund_stub",
                json=payload,
            )
            self.assertEqual(patched.status_code, 200, patched.text)

            created = client.post("/api/v1/customer-assistant/sessions", json={"context": {}})
            session_id = int(created.json()["data"]["id"])
            turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "react-profile-tool-policy"},
            )
            self.assertEqual(turn.status_code, 200, turn.text)
            tasks = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/tasks").json()["data"]["list"]
            events = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/events").json()["data"]["list"]

        task = tasks[0]
        react_failures = [
            event
            for event in events
            if event["type"] == "react_tool_call_failed" and event["source"] == "react_worker"
        ]
        self.assertEqual(task["workerType"], "react_worker")
        self.assertEqual(task["workerRef"], "configured_refund_react")
        self.assertEqual(task["status"], "FAILED")
        self.assertEqual(task["lastResult"]["error"]["code"], "TOOL_NOT_ALLOWED")
        self.assertEqual(react_failures[0]["payload"]["reason"], "not_allowed")
        self.assertEqual(turn.json()["data"]["proposedActions"], [])

    def test_react_worker_profile_refs_are_recorded_in_worker_evidence(self) -> None:
        payload = {
            "taskKey": "refund_ticket",
            "taskType": "REFUND",
            "workerType": "react_worker",
            "workerRef": "configured_refund_react",
            "modelPolicyRef": "demo-react-model",
            "promptRef": "demo-react-prompt",
            "toolRefs": ["lookup_order"],
            "toolPolicyRef": "strict-read-before-write",
            "riskPolicyRef": "manual_confirm_high_risk",
            "outputSchemaRef": "refund_react_result_v2",
            "enabled": True,
        }

        with TestClient(app) as client:
            patched = client.patch(
                "/api/v1/customer-assistant/worker-profiles/configured_refund_stub",
                json=payload,
            )
            self.assertEqual(patched.status_code, 200, patched.text)
            self.assertEqual(patched.json()["data"]["toolPolicyRef"], "strict-read-before-write")
            self.assertEqual(patched.json()["data"]["outputSchemaRef"], "refund_react_result_v2")

            created = client.post("/api/v1/customer-assistant/sessions", json={"context": {}})
            session_id = int(created.json()["data"]["id"])
            turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "react-profile-evidence"},
            )
            self.assertEqual(turn.status_code, 200, turn.text)
            task = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/tasks").json()["data"]["list"][0]

        config_refs = task["lastResult"]["evidence"]["workerConfigRefs"]
        self.assertEqual(task["status"], "COMPLETED")
        self.assertEqual(config_refs["workerRef"], "configured_refund_react")
        self.assertEqual(config_refs["modelPolicyRef"], "demo-react-model")
        self.assertEqual(config_refs["promptRef"], "demo-react-prompt")
        self.assertEqual(config_refs["toolPolicyRef"], "strict-read-before-write")
        self.assertEqual(config_refs["toolRefs"], ["lookup_order"])
        self.assertEqual(config_refs["riskPolicyRef"], "manual_confirm_high_risk")
        self.assertEqual(config_refs["outputSchemaRef"], "refund_react_result_v2")

    def test_react_worker_tool_policy_ref_can_require_manual_confirmation(self) -> None:
        payload = {
            "taskKey": "refund_ticket",
            "taskType": "REFUND",
            "workerType": "react_worker",
            "workerRef": "configured_refund_react",
            "modelPolicyRef": "demo-react-model",
            "promptRef": "demo-react-prompt",
            "toolRefs": ["lookup_order"],
            "toolPolicyRef": "manual_confirm_lookup_tools",
            "riskPolicyRef": "manual_confirm_high_risk",
            "outputSchemaRef": "refund_react_result_v2",
            "enabled": True,
        }

        with TestClient(app) as client:
            patched = client.patch(
                "/api/v1/customer-assistant/worker-profiles/configured_refund_stub",
                json=payload,
            )
            self.assertEqual(patched.status_code, 200, patched.text)

            created = client.post("/api/v1/customer-assistant/sessions", json={"context": {}})
            session_id = int(created.json()["data"]["id"])
            turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "react-profile-manual-confirm-tool"},
            )
            self.assertEqual(turn.status_code, 200, turn.text)
            turn_data = turn.json()["data"]
            task = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/tasks").json()["data"]["list"][0]
            events = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/events").json()["data"]["list"]

        completed_tool_calls = [
            event
            for event in events
            if event["type"] == "react_tool_call_completed" and event["payload"].get("tool") == "lookup_order"
        ]
        self.assertEqual(task["workerType"], "react_worker")
        self.assertEqual(task["status"], "WAITING")
        self.assertEqual(turn_data["proposedActions"][0]["actionType"], "lookup_order")
        self.assertEqual(task["lastResult"]["evidence"]["workerConfigRefs"]["toolPolicyRef"], "manual_confirm_lookup_tools")
        self.assertEqual(completed_tool_calls, [])

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session
