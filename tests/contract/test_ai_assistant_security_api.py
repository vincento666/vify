import unittest
from collections.abc import Generator
import os
import tempfile

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
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
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

    def tearDown(self) -> None:
        if self._previous_workspace_root is None:
            os.environ.pop("HIFY_WORKSPACE_ROOT", None)
        else:
            os.environ["HIFY_WORKSPACE_ROOT"] = self._previous_workspace_root
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._workspace_dir.cleanup()
        self._tmp_dir.cleanup()

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

    def test_approved_approval_resumes_tool_execution_and_completes_run(self) -> None:
        with TestClient(app) as client:
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
        self.assertEqual(inspector["approvalQueue"], [])
        self.assertEqual(inspector["approvalHistory"][0]["status"], "APPROVED")
        self.assertEqual(inspector["toolCalls"][0]["toolName"], "write_workspace_file")
        self.assertIn("approval.granted", [event["type"] for event in events])
        self.assertIn("tool.call_completed", [event["type"] for event in events])
        self.assertIn("run.completed", [event["type"] for event in events])

    def test_approved_write_continues_pending_readback_tool_call(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Security"}).json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "写入后读取确认",
                    "idempotencyKey": "security-approve-readback",
                    "approvalMode": "ask_each_time",
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
        self.assertIn("run.completed", [event["type"] for event in events])

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

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
