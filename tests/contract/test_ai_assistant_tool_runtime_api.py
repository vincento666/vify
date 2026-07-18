import unittest
from collections.abc import Generator
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.ai_assistant.domain import business_adapter
from app.modules.ai_assistant.domain.business_adapter import MockAviationAdapter
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.tools import RiskLevel, ToolManifest, ToolRegistry
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.web.router import get_ai_assistant_service
from tests.support.mysql import mysql8_unittest_database


class AiAssistantToolRuntimeApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_tool_runtime_contract",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._calls: list[dict[str, Any]] = []
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            ai_assistant_tool_profile="demo",
        )
        app.dependency_overrides[get_ai_assistant_service] = self._service_override

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_ai_assistant_service, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_tool_failure_is_returned_as_structured_observation_then_degraded_completion(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Tool runtime contract"})
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "try an unreliable tool",
                    "idempotencyKey": "tool-runtime-observation",
                    "toolName": "unstable_tool",
                    "toolInput": {"caseId": "case-tool-runtime"},
                    "approvalMode": "always_approve",
                },
            )
            run_id = turn.json()["data"].get("runId") if turn.status_code == 200 else None
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events") if run_id else None

        self.assertEqual(turn.status_code, 200, turn.text)
        data = turn.json()["data"]
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["toolCalls"][0]["status"], "FAILED")
        observation = data["toolCalls"][0]["output"]["observation"]
        self.assertEqual(observation["kind"], "tool_error")
        self.assertEqual(observation["toolName"], "unstable_tool")
        self.assertEqual(observation["error"]["code"], "TOOL_RUNTIME_ERROR")
        self.assertTrue(observation["modelVisible"])
        self.assertTrue(observation["retriable"])
        event_types = [event["type"] for event in events.json()["data"]["list"]]
        self.assertIn("tool.error_observation", event_types)
        self.assertIn("plan.revised", event_types)
        self.assertIn("tool.call_failed", event_types)
        self.assertIn("tool.self_correction_degraded", event_types)
        self.assertIn("plan.step_completed", event_types)
        self.assertIn("task.completed", event_types)
        self.assertIn("run.completed", event_types)
        self.assertNotIn("run.failed", event_types)
        after_tool_start = event_types[event_types.index("tool.call_started") :]
        self.assertNotIn("tool.call_completed", after_tool_start)

    def test_scheduled_tool_failure_short_circuits_followup_tools(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Scheduled failure"})
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "scheduled failure",
                    "idempotencyKey": "scheduled-failure-short-circuit",
                    "approvalMode": "always_approve",
                    "toolCalls": [
                        {"toolName": "approval_failing_tool", "toolInput": {"caseId": "case-scheduled-fails-first"}},
                        {"toolName": "after_tool", "toolInput": {"caseId": "case-scheduled-after"}},
                    ],
                },
            )
            run_id = turn.json()["data"].get("runId") if turn.status_code == 200 else None
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events") if run_id else None

        self.assertEqual(turn.status_code, 200, turn.text)
        data = turn.json()["data"]
        self.assertEqual(data["status"], "FAILED")
        self.assertEqual([tool["toolName"] for tool in data["toolCalls"]], ["approval_failing_tool"])
        self.assertNotIn("after_tool", [call.get("toolName") for call in self._calls])
        event_types = [event["type"] for event in events.json()["data"]["list"]]
        started_tools = [event["payload"].get("toolName") for event in events.json()["data"]["list"] if event["type"] == "tool.call_started"]
        self.assertEqual(started_tools, ["approval_failing_tool"])
        self.assertIn("tool.call_failed", event_types)
        self.assertIn("run.failed", event_types)

    def test_read_parallel_failure_records_terminal_events_for_started_siblings(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Parallel failure"})
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "parallel read failure",
                    "idempotencyKey": "read-parallel-terminal-audit",
                    "approvalMode": "always_approve",
                    "toolCalls": [
                        {"toolName": "parallel_failing_tool", "toolInput": {"caseId": "case-parallel-fails"}},
                        {"toolName": "parallel_after_tool", "toolInput": {"caseId": "case-parallel-after"}},
                    ],
                },
            )
            run_id = turn.json()["data"].get("runId") if turn.status_code == 200 else None
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events") if run_id else None

        self.assertEqual(turn.status_code, 200, turn.text)
        data = turn.json()["data"]
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(
            [tool["toolName"] for tool in data["toolCalls"]],
            ["parallel_failing_tool", "parallel_after_tool"],
        )
        statuses = {tool["toolName"]: tool["status"] for tool in data["toolCalls"]}
        self.assertEqual(statuses["parallel_failing_tool"], "FAILED")
        self.assertEqual(statuses["parallel_after_tool"], "COMPLETED")
        called_tool_names = [call.get("toolName") for call in self._calls]
        self.assertIn("parallel_failing_tool", called_tool_names)
        self.assertIn("parallel_after_tool", called_tool_names)
        event_list = events.json()["data"]["list"]
        terminal_events = [
            (event["type"], event["payload"].get("toolName"))
            for event in event_list
            if event["type"] in {"tool.call_failed", "tool.call_completed"}
        ]
        self.assertIn(("tool.call_failed", "parallel_failing_tool"), terminal_events)
        self.assertIn(("tool.call_completed", "parallel_after_tool"), terminal_events)
        event_types = [event["type"] for event in event_list]
        self.assertIn("tool.self_correction_degraded", event_types)
        self.assertIn("run.completed", event_types)
        self.assertNotIn("run.failed", event_types)
        run_completed_index = event_types.index("run.completed")
        terminal_indexes = [
            index
            for index, event in enumerate(event_list)
            if (event["type"], event["payload"].get("toolName"))
            in {
                ("tool.call_failed", "parallel_failing_tool"),
                ("tool.call_completed", "parallel_after_tool"),
            }
        ]
        self.assertTrue(terminal_indexes)
        self.assertLess(max(terminal_indexes), run_completed_index)

    def test_mock_business_adapter_tool_runs_through_harness_approval_and_audit_path(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Adapter contract"})
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "mock refund",
                    "idempotencyKey": "mock-adapter-approval",
                    "toolName": "mock_aviation.refund",
                    "toolInput": {"caseId": "case-adapter-1", "passengerId": "PAX-1", "request": "refund"},
                    "approvalMode": "smart_approval",
                },
            )
            data = turn.json()["data"]
            approval_id = data["approvalId"]
            approved = client.post(
                f"/api/v1/ai-assistant/approvals/{approval_id}/approve",
                json={"actorId": "operator-adapter"},
            )
            run = client.get(f"/api/v1/ai-assistant/runs/{data['runId']}").json()["data"]
            inspector = client.get(f"/api/v1/ai-assistant/runs/{data['runId']}/inspector").json()["data"]
            events = client.get(f"/api/v1/ai-assistant/runs/{data['runId']}/events").json()["data"]["list"]

        self.assertEqual(turn.status_code, 200, turn.text)
        self.assertEqual(data["status"], "WAITING_APPROVAL")
        self.assertTrue(data["approvalRequired"])
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(run["status"], "COMPLETED")
        tool = run["result"]["toolCalls"][0]
        self.assertEqual(tool["toolName"], "mock_aviation.refund")
        self.assertEqual(tool["status"], "COMPLETED")
        self.assertEqual(tool["output"]["status"], "MOCK_ACCEPTED")
        self.assertEqual(tool["output"]["audit"]["adapterName"], "mock_aviation")
        self.assertTrue(tool["output"]["audit"]["mockOnly"])
        self.assertFalse(tool["output"]["audit"]["realAviationRulesApplied"])
        self.assertEqual(tool["output"]["compensationTransaction"]["status"], "MOCK_COMPENSATION_READY")
        self.assertEqual(tool["input"]["_toolRuntime"]["idempotencyKey"], "mock_aviation.refund:case-adapter-1")
        self.assertEqual(inspector["toolCalls"][0]["output"]["audit"], tool["output"]["audit"])
        event_types = [event["type"] for event in events]
        self.assertIn("approval.required", event_types)
        self.assertIn("approval.granted", event_types)
        self.assertIn("context.budget_estimated", event_types)
        self.assertIn("tool.call_completed", event_types)

    def test_approved_tool_failure_stays_failed_observation_instead_of_successful_completion(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Approval failure"})
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "approval then fail",
                    "idempotencyKey": "approval-failure-observation",
                    "toolName": "approval_failing_tool",
                    "toolInput": {"caseId": "case-approved-fails"},
                    "approvalMode": "smart_approval",
                },
            )
            data = turn.json()["data"]
            approval_id = data["approvalId"]
            approved = client.post(
                f"/api/v1/ai-assistant/approvals/{approval_id}/approve",
                json={"actorId": "operator-failure"},
            )
            run = client.get(f"/api/v1/ai-assistant/runs/{data['runId']}").json()["data"]
            events = client.get(f"/api/v1/ai-assistant/runs/{data['runId']}/events").json()["data"]["list"]

        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(run["status"], "FAILED")
        tool = run["result"]["toolCalls"][0]
        self.assertEqual(tool["toolName"], "approval_failing_tool")
        self.assertEqual(tool["status"], "FAILED")
        self.assertEqual(tool["output"]["observation"]["kind"], "tool_error")
        self.assertEqual(tool["output"]["observation"]["error"]["code"], "TOOL_RUNTIME_ERROR")
        self.assertEqual(run["result"]["plan"]["status"], "BLOCKED")
        event_types = [event["type"] for event in events]
        self.assertIn("tool.error_observation", event_types)
        self.assertIn("plan.revised", event_types)
        self.assertIn("plan.blocked", event_types)
        self.assertIn("task.blocked", event_types)
        self.assertIn("run.failed", event_types)
        after_approval = event_types[event_types.index("approval.granted") :]
        self.assertIn("tool.call_failed", after_approval)
        self.assertNotIn("tool.call_completed", after_approval)
        self.assertNotIn("plan.step_completed", after_approval)
        self.assertNotIn("task.completed", after_approval)

    def test_approved_tool_failure_short_circuits_pending_followup_tools(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Approval failure pending"})
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "approval fails before followup",
                    "idempotencyKey": "approval-failure-short-circuit",
                    "approvalMode": "smart_approval",
                    "toolCalls": [
                        {"toolName": "approval_failing_tool", "toolInput": {"caseId": "case-approved-fails-first"}},
                        {"toolName": "after_tool", "toolInput": {"caseId": "case-after-tool"}},
                    ],
                },
            )
            data = turn.json()["data"]
            approval_id = data["approvalId"]
            approved = client.post(
                f"/api/v1/ai-assistant/approvals/{approval_id}/approve",
                json={"actorId": "operator-failure"},
            )
            run = client.get(f"/api/v1/ai-assistant/runs/{data['runId']}").json()["data"]
            events = client.get(f"/api/v1/ai-assistant/runs/{data['runId']}/events").json()["data"]["list"]

        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(run["status"], "FAILED")
        self.assertEqual([tool["toolName"] for tool in run["result"]["toolCalls"]], ["approval_failing_tool"])
        self.assertNotIn("after_tool", [call.get("toolName") for call in self._calls])
        started_tools = [event["payload"].get("toolName") for event in events if event["type"] == "tool.call_started"]
        self.assertEqual(started_tools, ["approval_failing_tool"])

    def _service_override(self) -> Generator[AiAssistantHarnessService, None, None]:
        with self._factory() as session:
            tools = {
                "unstable_tool": (_unstable_manifest(), self._unstable_tool),
                "approval_failing_tool": (_approval_failing_manifest(), self._approval_failing_tool),
                "after_tool": (_after_manifest(), self._after_tool),
                "parallel_failing_tool": (_parallel_failing_manifest(), self._parallel_failing_tool),
                "parallel_after_tool": (_parallel_after_manifest(), self._parallel_after_tool),
            }
            self.assertTrue(
                hasattr(business_adapter, "tool_entries_for_business_adapter"),
                "business adapter seam must expose tool_entries_for_business_adapter()",
            )
            tools.update(business_adapter.tool_entries_for_business_adapter(MockAviationAdapter()))
            yield AiAssistantHarnessService(
                AiAssistantRepository(session),
                tool_registry=ToolRegistry(tools),
            )

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session

    def _unstable_tool(self, payload: dict[str, Any]):
        self._calls.append(payload)
        raise RuntimeError("simulated 5xx")

    def _approval_failing_tool(self, payload: dict[str, Any]):
        self._calls.append(payload)
        raise RuntimeError("approved side effect failed")

    def _after_tool(self, payload: dict[str, Any]):
        self._calls.append(payload | {"toolName": "after_tool"})
        from app.modules.ai_assistant.domain.tools import ToolResult

        return ToolResult(status="COMPLETED", output={"after": True})

    def _parallel_failing_tool(self, payload: dict[str, Any]):
        self._calls.append(payload | {"toolName": "parallel_failing_tool"})
        raise RuntimeError("parallel read failed")

    def _parallel_after_tool(self, payload: dict[str, Any]):
        self._calls.append(payload | {"toolName": "parallel_after_tool"})
        from app.modules.ai_assistant.domain.tools import ToolResult

        return ToolResult(status="COMPLETED", output={"parallelAfter": True})


def _unstable_manifest() -> ToolManifest:
    return ToolManifest(
        name="unstable_tool",
        description="Tool that simulates a transient backend failure.",
        input_schema={"type": "object", "properties": {"caseId": {"type": "string"}}},
        output_schema={"type": "object"},
        timeout_ms=50,
        risk_level=RiskLevel.READ,
        read_resources=[],
        write_resources=[],
        policy_ref="ai_assistant_read_only",
    )


def _approval_failing_manifest() -> ToolManifest:
    return ToolManifest(
        name="approval_failing_tool",
        description="Business write tool that fails after approval.",
        input_schema={"type": "object", "properties": {"caseId": {"type": "string"}}},
        output_schema={"type": "object"},
        timeout_ms=50,
        risk_level=RiskLevel.BUSINESS_WRITE,
        read_resources=[],
        write_resources=["business:test:{caseId}"],
        policy_ref="ai_assistant_business_write_requires_approval",
    )


def _after_manifest() -> ToolManifest:
    return ToolManifest(
        name="after_tool",
        description="Read-only follow-up tool that must not run after approved failure.",
        input_schema={"type": "object", "properties": {"caseId": {"type": "string"}}},
        output_schema={"type": "object"},
        timeout_ms=50,
        risk_level=RiskLevel.READ,
        read_resources=["business:test:{caseId}"],
        write_resources=[],
        policy_ref="ai_assistant_read_only",
    )


def _parallel_failing_manifest() -> ToolManifest:
    return ToolManifest(
        name="parallel_failing_tool",
        description="Read-only tool that fails inside a read-parallel batch.",
        input_schema={"type": "object", "properties": {"caseId": {"type": "string"}}},
        output_schema={"type": "object"},
        timeout_ms=50,
        risk_level=RiskLevel.READ,
        read_resources=["parallel:test:{caseId}"],
        write_resources=[],
        policy_ref="ai_assistant_read_only",
    )


def _parallel_after_manifest() -> ToolManifest:
    return ToolManifest(
        name="parallel_after_tool",
        description="Read-only sibling that still needs terminal audit after another parallel read fails.",
        input_schema={"type": "object", "properties": {"caseId": {"type": "string"}}},
        output_schema={"type": "object"},
        timeout_ms=50,
        risk_level=RiskLevel.READ,
        read_resources=["parallel:test:{caseId}"],
        write_resources=[],
        policy_ref="ai_assistant_read_only",
    )


if __name__ == "__main__":
    unittest.main()
