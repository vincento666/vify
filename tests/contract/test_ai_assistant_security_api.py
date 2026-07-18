import unittest
from collections.abc import Generator
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.core.host.context import RequestContext
from app.core.host.dependencies import get_request_context
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantSecurityApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_security",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._workspace_dir = tempfile.TemporaryDirectory()
        self._previous_workspace_root = os.environ.get("HIFY_WORKSPACE_ROOT")
        os.environ["HIFY_WORKSPACE_ROOT"] = self._workspace_dir.name
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            ai_assistant_tool_profile="demo",
        )

    def tearDown(self) -> None:
        if self._previous_workspace_root is None:
            os.environ.pop("HIFY_WORKSPACE_ROOT", None)
        else:
            os.environ["HIFY_WORKSPACE_ROOT"] = self._previous_workspace_root
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._workspace_dir.cleanup()

    def test_smart_approval_read_only_tool_runs_without_approval(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Security"}).json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "read this",
                    "idempotencyKey": "security-read",
                    "approvalMode": "smart_approval",
                    "toolName": "echo_context",
                },
            )
            run_id = message.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]
            approvals = client.get("/api/v1/ai-assistant/approvals").json()["data"]["list"]

        self.assertEqual(message.json()["data"]["status"], "COMPLETED")
        self.assertEqual(approvals, [])
        self.assertNotIn("approval.required", [event["type"] for event in events])

    def test_high_risk_business_write_pauses_with_approval_and_proposed_action(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Security"}).json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "update customer profile",
                    "idempotencyKey": "security-write",
                    "approvalMode": "smart_approval",
                    "toolName": "update_customer_profile",
                    "toolInput": {"customerId": "C-1", "field": "tier", "value": "gold"},
                },
            )
            run_id = message.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]
            approvals = client.get("/api/v1/ai-assistant/approvals").json()["data"]["list"]

        event_types = [event["type"] for event in events]
        self.assertEqual(message.json()["data"]["status"], "WAITING_APPROVAL")
        self.assertEqual(message.json()["data"]["approvalRequired"], True)
        self.assertEqual(message.json()["data"]["toolCalls"], [])
        self.assertIn("approval.required", event_types)
        self.assertIn("proposed_action.created", event_types)
        self.assertEqual(approvals[0]["status"], "PENDING")
        self.assertEqual(approvals[0]["riskLevel"], "BUSINESS_WRITE")

    def test_denied_approval_records_decision_and_does_not_execute(self) -> None:
        with TestClient(app) as client:
            client.headers.update({"X-Hify-Actor-Id": "operator-1"})
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Security"}).json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "update customer profile",
                    "idempotencyKey": "security-deny",
                    "approvalMode": "ask_each_time",
                    "toolName": "update_customer_profile",
                    "toolInput": {"customerId": "C-1"},
                },
            )
            approval_id = client.get("/api/v1/ai-assistant/approvals").json()["data"]["list"][0]["id"]
            denied = client.post(
                f"/api/v1/ai-assistant/approvals/{approval_id}/deny",
                json={"actorId": "operator-1", "reason": "Unsafe change"},
            )
            run_id = message.json()["data"]["runId"]
            run = client.get(f"/api/v1/ai-assistant/runs/{run_id}").json()["data"]
            inspector = client.get(f"/api/v1/ai-assistant/runs/{run_id}/inspector").json()["data"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]

        self.assertEqual(denied.json()["data"]["status"], "DENIED")
        self.assertEqual(denied.json()["data"]["decidedBy"], "operator-1")
        self.assertEqual(run["status"], "DENIED")
        self.assertEqual(run["result"]["approvalRequired"], False)
        self.assertEqual(inspector["approvalQueue"], [])
        self.assertEqual(inspector["approvalHistory"][0]["status"], "DENIED")
        self.assertIn("approval.denied", [event["type"] for event in events])
        self.assertNotIn("tool.call_completed", [event["type"] for event in events])

    def test_approval_audit_actor_comes_from_server_context_not_request_body(self) -> None:
        headers = {
            "X-Hify-Actor-Id": "trusted-operator",
            "X-Hify-Tenant-Id": "trusted-tenant",
            "X-Hify-Source": "trusted-auth-adapter",
            "X-Request-Id": "approval-audit-request",
        }
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                json={"title": "Security"},
                headers=headers,
            ).json()["data"]["id"]
            client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "update customer profile",
                    "idempotencyKey": "server-derived-actor",
                    "approvalMode": "ask_each_time",
                    "toolName": "update_customer_profile",
                    "toolInput": {"customerId": "C-actor"},
                },
                headers=headers,
            )
            approval_id = client.get(
                "/api/v1/ai-assistant/approvals",
                headers=headers,
            ).json()["data"]["list"][0]["id"]
            approved = client.post(
                f"/api/v1/ai-assistant/approvals/{approval_id}/approve",
                json={"actorId": "spoofed-body-actor"},
                headers=headers,
            )
            events = client.get(
                f"/api/v1/ai-assistant/runs/{approved.json()['data']['runId']}/events",
                headers=headers,
            ).json()["data"]["list"]

        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["data"]["decidedBy"], "trusted-operator")
        approval_event = next(event for event in events if event["type"] == "approval.granted")
        self.assertEqual(approval_event["payload"]["actorAudit"]["actorId"], "trusted-operator")
        self.assertEqual(approval_event["payload"]["actorAudit"]["tenantId"], "trusted-tenant")
        self.assertEqual(
            approval_event["payload"]["actorAudit"]["requestId"],
            "approval-audit-request",
        )
        self.assertEqual(
            approval_event["payload"]["legacyActorIdField"],
            "ignored_mismatch",
        )

    def test_production_service_wires_fail_closed_approval_policy(self) -> None:
        script = Path(self._workspace_dir.name) / "tmp" / "production-policy.mjs"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("console.log('must not run')\n", encoding="utf-8")
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            deployment_environment="production",
            host_identity_mode="trusted_state",
        )
        app.dependency_overrides[get_request_context] = lambda: RequestContext(
            actor_id="trusted-production-user",
            tenant_id="trusted-production-tenant",
            org_id="trusted-production-org",
            permissions=("ai_assistant:operate",),
            source="trusted-auth-adapter",
        )

        try:
            with TestClient(app) as client:
                session_id = client.post(
                    "/api/v1/ai-assistant/sessions",
                    json={"title": "Production Security"},
                ).json()["data"]["id"]
                message = client.post(
                    f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                    json={
                        "message": "run controlled shell",
                        "idempotencyKey": "production-policy-deny",
                        "approvalMode": "always_approve",
                        "toolName": "run_shell",
                        "toolInput": {"command": "node tmp/production-policy.mjs"},
                    },
                )
        finally:
            app.dependency_overrides.pop(get_request_context, None)

        self.assertEqual(message.status_code, 200, message.text)
        self.assertEqual(message.json()["data"]["status"], "DENIED")

    def test_production_principal_without_ai_assistant_permission_is_forbidden(
        self,
    ) -> None:
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            deployment_environment="production",
            host_identity_mode="trusted_state",
        )
        app.dependency_overrides[get_request_context] = lambda: RequestContext(
            actor_id="authenticated-without-product-access",
            tenant_id="trusted-production-tenant",
            org_id="trusted-production-org",
            source="trusted-auth-adapter",
        )

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/ai-assistant/sessions",
                    json={"title": "Must be forbidden"},
                )
        finally:
            app.dependency_overrides.pop(get_request_context, None)

        self.assertEqual(response.status_code, 403, response.text)

    def test_production_read_permission_cannot_mutate_sessions(self) -> None:
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            deployment_environment="production",
            host_identity_mode="trusted_state",
        )
        app.dependency_overrides[get_request_context] = lambda: RequestContext(
            actor_id="read-only-user",
            tenant_id="trusted-production-tenant",
            org_id="trusted-production-org",
            permissions=("ai_assistant:read",),
            source="trusted-auth-adapter",
        )

        try:
            with TestClient(app) as client:
                tools = client.get("/api/v1/ai-assistant/tools")
                create = client.post(
                    "/api/v1/ai-assistant/sessions",
                    json={"title": "Read only"},
                )
        finally:
            app.dependency_overrides.pop(get_request_context, None)

        self.assertEqual(tools.status_code, 200, tools.text)
        self.assertEqual(create.status_code, 403, create.text)

    def test_approved_approval_resumes_tool_execution_and_completes_run(self) -> None:
        with TestClient(app) as client:
            client.headers.update({"X-Hify-Actor-Id": "operator-2"})
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Security"}).json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "write workspace file after approval",
                    "idempotencyKey": "security-approve",
                    "approvalMode": "ask_each_time",
                    "toolName": "write_workspace_file",
                    "toolInput": {"path": "approved.txt", "content": "approved content"},
                },
            )
            approval_id = client.get("/api/v1/ai-assistant/approvals").json()["data"]["list"][0]["id"]
            approved = client.post(
                f"/api/v1/ai-assistant/approvals/{approval_id}/approve",
                json={"actorId": "operator-2"},
            )
            run_id = message.json()["data"]["runId"]
            run = client.get(f"/api/v1/ai-assistant/runs/{run_id}").json()["data"]
            inspector = client.get(f"/api/v1/ai-assistant/runs/{run_id}/inspector").json()["data"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]

        self.assertEqual(approved.json()["data"]["status"], "APPROVED")
        self.assertEqual(approved.json()["data"]["decidedBy"], "operator-2")
        self.assertEqual(run["status"], "COMPLETED")
        self.assertEqual(run["result"]["approvalRequired"], False)
        self.assertEqual(run["result"]["toolCalls"][0]["toolName"], "write_workspace_file")
        self.assertEqual(run["result"]["plan"]["status"], "COMPLETED")
        self.assertEqual(run["result"]["plan"]["currentStep"]["status"], "COMPLETED")
        self.assertEqual(run["result"]["plan"]["steps"][0]["status"], "COMPLETED")
        self.assertEqual(inspector["approvalQueue"], [])
        self.assertEqual(inspector["approvalHistory"][0]["status"], "APPROVED")
        self.assertEqual(inspector["toolCalls"][0]["toolName"], "write_workspace_file")
        self.assertEqual(inspector["plan"]["status"], "COMPLETED")
        self.assertEqual(inspector["plan"]["currentStep"]["status"], "COMPLETED")
        self.assertEqual(inspector["plan"]["steps"][0]["status"], "COMPLETED")
        event_types = [event["type"] for event in events]
        self.assertIn("approval.granted", event_types)
        self.assertIn("plan.revised", event_types)
        self.assertIn("plan.step_started", event_types)
        self.assertIn("tool.call_completed", event_types)
        self.assertIn("plan.step_completed", event_types)
        self.assertIn("task.completed", event_types)
        self.assertIn("run.completed", event_types)
        task_updates = [event["payload"] for event in events if event["type"] == "task.updated"]
        self.assertEqual(task_updates[-1]["planStatus"], "COMPLETED")
        self.assertEqual(task_updates[-1]["currentStep"]["status"], "COMPLETED")

    def test_approved_write_continues_pending_readback_tool_call(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Security"}).json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "写入后读取确认",
                    "idempotencyKey": "security-approve-readback",
                    "approvalMode": "smart_approval",
                    "toolCalls": [
                        {
                            "toolName": "write_workspace_file",
                            "toolInput": {"path": "approved-readback.txt", "content": "approved readback content"},
                        },
                        {"toolName": "read_workspace_file", "toolInput": {"path": "approved-readback.txt"}},
                    ],
                },
            )
            approval_id = client.get("/api/v1/ai-assistant/approvals").json()["data"]["list"][0]["id"]
            approved = client.post(
                f"/api/v1/ai-assistant/approvals/{approval_id}/approve",
                json={"actorId": "operator-2"},
            )
            run_id = message.json()["data"]["runId"]
            run = client.get(f"/api/v1/ai-assistant/runs/{run_id}").json()["data"]
            inspector = client.get(f"/api/v1/ai-assistant/runs/{run_id}/inspector").json()["data"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]

        self.assertEqual(approved.json()["data"]["status"], "APPROVED")
        self.assertEqual(run["status"], "COMPLETED")
        self.assertEqual(
            [tool["toolName"] for tool in run["result"]["toolCalls"]],
            ["write_workspace_file", "read_workspace_file"],
        )
        self.assertEqual(
            [tool["toolName"] for tool in inspector["toolCalls"]],
            ["write_workspace_file", "read_workspace_file"],
        )
        self.assertIn("approved readback content", run["result"]["toolCalls"][1]["output"]["content"])
        self.assertEqual(run["result"]["plan"]["status"], "COMPLETED")
        self.assertEqual(inspector["plan"]["status"], "COMPLETED")
        self.assertEqual(inspector["plan"]["currentStep"]["status"], "COMPLETED")
        self.assertEqual(inspector["plan"]["steps"][0]["status"], "COMPLETED")
        self.assertEqual(inspector["plan"]["steps"][1]["status"], "COMPLETED")
        event_types = [event["type"] for event in events]
        self.assertIn("plan.revised", event_types)
        self.assertIn("plan.step_completed", event_types)
        self.assertIn("task.completed", event_types)
        self.assertIn("run.completed", event_types)

    def test_unsafe_shell_command_is_blocked_by_sandbox_policy(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Security"}).json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "run shell",
                    "idempotencyKey": "security-sandbox",
                    "approvalMode": "always_approve",
                    "toolName": "run_shell",
                    "toolInput": {"command": "rm -rf /tmp/hify"},
                },
            )
            run_id = message.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]

        self.assertEqual(message.json()["data"]["status"], "DENIED")
        self.assertEqual(message.json()["data"]["sandboxDenied"], True)
        self.assertIn("sandbox.denied", [event["type"] for event in events])
        self.assertNotIn("tool.call_started", [event["type"] for event in events])

    def test_always_approve_runs_controlled_workspace_command(self) -> None:
        script = Path(self._workspace_dir.name) / "tmp" / "controlled-shell-api.mjs"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("console.log('PASS controlled shell api')\n", encoding="utf-8")

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Security"}).json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "run controlled shell",
                    "idempotencyKey": "security-controlled-shell",
                    "approvalMode": "always_approve",
                    "toolName": "run_shell",
                    "toolInput": {"command": "node tmp/controlled-shell-api.mjs"},
                },
            )
            run_id = message.json()["data"]["runId"]
            run = client.get(f"/api/v1/ai-assistant/runs/{run_id}").json()["data"]
            inspector = client.get(f"/api/v1/ai-assistant/runs/{run_id}/inspector").json()["data"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]
            approvals = client.get("/api/v1/ai-assistant/approvals").json()["data"]["list"]

        event_types = [event["type"] for event in events]
        self.assertEqual(message.json()["data"]["status"], "COMPLETED")
        self.assertIn("PASS controlled shell api", message.json()["data"]["finalAnswer"])
        self.assertFalse(message.json()["data"]["approvalRequired"])
        self.assertFalse(message.json()["data"]["sandboxDenied"])
        self.assertEqual(run["status"], "COMPLETED")
        self.assertEqual(approvals, [])
        self.assertIn("tool.call_started", event_types)
        self.assertIn("tool.call_output", event_types)
        self.assertIn("tool.call_completed", event_types)
        self.assertNotIn("sandbox.denied", event_types)
        self.assertEqual(inspector["toolCalls"][0]["toolName"], "run_shell")
        self.assertEqual(inspector["toolCalls"][0]["output"]["exitCode"], 0)
        self.assertIn("PASS controlled shell api", inspector["toolCalls"][0]["output"]["stdout"])

    def test_always_approve_write_is_still_bounded_by_policy_sandbox_and_db_lock_events(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Security"}).json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "write with safety gates",
                    "idempotencyKey": "security-gated-write",
                    "approvalMode": "always_approve",
                    "toolName": "write_workspace_file",
                    "toolInput": {"path": "gated.txt", "content": "safe content"},
                },
            )
            run_id = message.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]
            run = client.get(f"/api/v1/ai-assistant/runs/{run_id}").json()["data"]

        self.assertEqual(message.json()["data"]["status"], "COMPLETED")
        event_types = [event["type"] for event in events]
        self.assertIn("permission.evaluated", event_types)
        self.assertIn("sandbox.evaluated", event_types)
        self.assertIn("resource_lock.acquire_requested", event_types)
        self.assertIn("resource_lock.acquired", event_types)
        self.assertIn("resource_lock.released", event_types)
        permission = next(event["payload"] for event in events if event["type"] == "permission.evaluated")
        sandbox = next(event["payload"] for event in events if event["type"] == "sandbox.evaluated")
        acquired = next(event["payload"] for event in events if event["type"] == "resource_lock.acquired")
        released = next(event["payload"] for event in events if event["type"] == "resource_lock.released")
        self.assertEqual(permission["toolName"], "write_workspace_file")
        self.assertEqual(permission["approvalMode"], "always_approve")
        self.assertEqual(permission["decision"], "allow")
        self.assertEqual(sandbox["toolName"], "write_workspace_file")
        self.assertEqual(sandbox["verdict"], "allow")
        self.assertEqual(acquired["resourceKey"], "file:gated.txt")
        self.assertEqual(acquired["mode"], "WRITE")
        self.assertEqual(released["fencingToken"], acquired["fencingToken"])
        self.assertEqual(run["result"]["toolCalls"][0]["output"]["lock"]["scope"], "db")
        self.assertEqual(run["result"]["toolCalls"][0]["output"]["lock"]["fencingToken"], acquired["fencingToken"])

    def test_contended_db_resource_lock_returns_observation_without_executing_tool(self) -> None:
        from app.modules.ai_assistant.domain.resource_lock import ResourceLockManager, ResourceLockMode
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        with self._factory() as session:
            held = ResourceLockManager(AiAssistantRepository(session)).acquire(
                resource_key="file:locked.txt",
                mode=ResourceLockMode.WRITE,
                owner_session_id=900,
                owner_run_id=901,
                ttl_seconds=60,
            )
            self.assertEqual(held.status, "ACQUIRED")

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Security"}).json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "write contended file",
                    "idempotencyKey": "security-contended-write",
                    "approvalMode": "always_approve",
                    "toolName": "write_workspace_file",
                    "toolInput": {"path": "locked.txt", "content": "should not write"},
                },
            )
            run_id = message.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]
            run = client.get(f"/api/v1/ai-assistant/runs/{run_id}").json()["data"]

        self.assertEqual(message.json()["data"]["status"], "FAILED")
        self.assertFalse((Path(self._workspace_dir.name) / "locked.txt").exists())
        event_types = [event["type"] for event in events]
        self.assertIn("resource_lock.contended", event_types)
        self.assertNotIn("tool.call_started", event_types)
        tool_call = run["result"]["toolCalls"][0]
        self.assertEqual(tool_call["status"], "FAILED")
        self.assertEqual(tool_call["output"]["observation"]["error"]["code"], "RESOURCE_LOCK_CONTENDED")

    def test_session_policy_path_rule_uses_canonical_workspace_path(self) -> None:
        Path(self._workspace_dir.name, "AGENTS.md").write_text("rules", encoding="utf-8")
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                json={
                    "title": "Canonical policy",
                    "context": {
                        "aiAssistantPolicy": {
                            "rules": [
                                {
                                    "id": "deny-agents",
                                    "match": {"tool": "read_workspace_file", "path": "AGENTS.md"},
                                    "effect": "deny",
                                    "reason": "AGENTS.md reads disabled",
                                }
                            ]
                        }
                    },
                },
            ).json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "read agents",
                    "idempotencyKey": "security-canonical-policy",
                    "approvalMode": "always_approve",
                    "toolName": "read_workspace_file",
                    "toolInput": {"path": "./AGENTS.md"},
                },
            )
            run_id = message.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]

        permission = next(event["payload"] for event in events if event["type"] == "permission.evaluated")
        self.assertEqual(message.json()["data"]["status"], "DENIED")
        self.assertEqual(permission["decision"], "deny")
        self.assertEqual(permission["matchedRuleId"], "deny-agents")

    def test_equivalent_workspace_paths_share_same_db_resource_lock(self) -> None:
        from app.modules.ai_assistant.domain.resource_lock import ResourceLockManager, ResourceLockMode
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        with self._factory() as session:
            held = ResourceLockManager(AiAssistantRepository(session)).acquire(
                resource_key="file:locked-equivalent.txt",
                mode=ResourceLockMode.WRITE,
                owner_session_id=900,
                owner_run_id=902,
                ttl_seconds=60,
            )
            self.assertEqual(held.status, "ACQUIRED")

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Canonical lock"}).json()[
                "data"
            ]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "write equivalent path",
                    "idempotencyKey": "security-canonical-lock",
                    "approvalMode": "always_approve",
                    "toolName": "write_workspace_file",
                    "toolInput": {"path": "./locked-equivalent.txt", "content": "should not write"},
                },
            )
            run_id = message.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]

        self.assertEqual(message.json()["data"]["status"], "FAILED")
        self.assertFalse((Path(self._workspace_dir.name) / "locked-equivalent.txt").exists())
        self.assertIn("resource_lock.contended", [event["type"] for event in events])

    def test_sandbox_does_not_leak_non_allowlisted_env_and_redacts_secret_output(self) -> None:
        previous_secret = os.environ.get("LEAK_ME")
        os.environ["LEAK_ME"] = "super-secret-env-value"
        script = Path(self._workspace_dir.name) / "tmp" / "print-env.mjs"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("console.log(process.env.LEAK_ME || 'MISSING')\n", encoding="utf-8")
        try:
            with TestClient(app) as client:
                session_id = client.post(
                    "/api/v1/ai-assistant/sessions",
                    json={
                        "title": "Sandbox env",
                        "context": {
                            "aiAssistantSandbox": {
                                "envAllowlist": [],
                                "secretValues": ["super-secret-env-value"],
                                "allowedExecutables": ["node"],
                            }
                        },
                    },
                ).json()["data"]["id"]
                message = client.post(
                    f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                    json={
                        "message": "run env check",
                        "idempotencyKey": "security-sandbox-env",
                        "approvalMode": "always_approve",
                        "toolName": "run_shell",
                        "toolInput": {"command": "node tmp/print-env.mjs"},
                    },
                )
                run_id = message.json()["data"]["runId"]
                run = client.get(f"/api/v1/ai-assistant/runs/{run_id}").json()["data"]
        finally:
            if previous_secret is None:
                os.environ.pop("LEAK_ME", None)
            else:
                os.environ["LEAK_ME"] = previous_secret

        output = run["result"]["toolCalls"][0]["output"]
        self.assertEqual(message.json()["data"]["status"], "COMPLETED")
        self.assertIn("MISSING", output["stdout"])
        self.assertNotIn("super-secret-env-value", output["stdout"])

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
