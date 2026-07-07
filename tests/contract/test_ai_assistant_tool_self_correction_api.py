import time
import unittest
from collections.abc import Generator
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.tools import RiskLevel, ToolManifest, ToolRegistry, ToolResult
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.web.router import get_ai_assistant_service
from tests.support.mysql import mysql8_unittest_database


class AiAssistantToolSelfCorrectionApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_tool_self_correction_contract",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._calls: list[dict[str, Any]] = []
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
        app.dependency_overrides[get_ai_assistant_service] = self._service_override

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_ai_assistant_service, None)
        self._engine.dispose()

    def test_recoverable_5xx_observation_retries_with_repaired_arguments_and_completes(self) -> None:
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                json={"title": "Self correction contract"},
            ).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "repair a transient lookup",
                    "idempotencyKey": "self-correction-repair-5xx",
                    "toolName": "repairable_5xx_tool",
                    "toolInput": {
                        "caseId": "bad",
                        "_selfCorrection": {"retryToolInput": {"caseId": "good"}},
                    },
                    "approvalMode": "always_approve",
                    "aiAssistantBudget": {"maxToolRepairAttempts": 1},
                },
            )
            run_id = turn.json()["data"].get("runId") if turn.status_code == 200 else None
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events") if run_id else None
            audit = client.get(f"/api/v1/ai-assistant/runs/{run_id}/audit") if run_id else None

        self.assertEqual(turn.status_code, 200, turn.text)
        data = turn.json()["data"]
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual([tool["status"] for tool in data["toolCalls"]], ["FAILED", "COMPLETED"])
        self.assertEqual(data["toolCalls"][0]["output"]["observation"]["error"]["code"], "TOOL_RUNTIME_ERROR")
        self.assertEqual(data["toolCalls"][1]["input"]["caseId"], "good")
        self.assertIn("repaired", data["finalAnswer"])
        event_types = [event["type"] for event in events.json()["data"]["list"]]
        self.assertIn("tool.error_observation", event_types)
        self.assertIn("tool.self_correction_started", event_types)
        self.assertIn("tool.self_correction_completed", event_types)
        self.assertIn("plan.revised", event_types)
        self.assertIn("task.updated", event_types)
        self.assertIn("run.completed", event_types)
        self.assertNotIn("run.failed", event_types)
        self.assertEqual([call["caseId"] for call in self._calls], ["bad", "bad", "good"])
        audit_payload = audit.json()["data"]
        self.assertGreaterEqual(audit_payload["budget"]["tool"]["attempts"], 3)
        self.assertTrue(any(span["kind"] == "tool" for span in audit_payload["trace"]["spans"]))
        self.assertTrue(audit_payload["audit"]["selfCorrections"])
        self.assertTrue(
            any(event["type"] == "tool.self_correction_completed" for event in audit_payload["audit"]["selfCorrections"])
        )

    def test_rate_limit_observation_selects_fallback_tool_and_completes(self) -> None:
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                json={"title": "Self correction fallback"},
            ).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "fallback after rate limit",
                    "idempotencyKey": "self-correction-rate-fallback",
                    "toolName": "rate_limited_tool",
                    "toolInput": {
                        "caseId": "rate-limit",
                        "_selfCorrection": {
                            "fallbackToolName": "fallback_lookup_tool",
                            "fallbackToolInput": {"caseId": "fallback"},
                        },
                    },
                    "approvalMode": "always_approve",
                    "aiAssistantBudget": {"maxToolRepairAttempts": 1},
                },
            )
            run_id = turn.json()["data"].get("runId") if turn.status_code == 200 else None
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events") if run_id else None

        self.assertEqual(turn.status_code, 200, turn.text)
        data = turn.json()["data"]
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual([tool["toolName"] for tool in data["toolCalls"]], ["rate_limited_tool", "fallback_lookup_tool"])
        self.assertEqual(data["toolCalls"][0]["output"]["observation"]["error"]["code"], "TOOL_RATE_LIMIT")
        self.assertEqual(data["toolCalls"][1]["status"], "COMPLETED")
        event_types = [event["type"] for event in events.json()["data"]["list"]]
        self.assertIn("tool.self_correction_fallback_selected", event_types)
        self.assertIn("tool.self_correction_completed", event_types)
        self.assertIn("run.completed", event_types)

    def test_repair_budget_exhaustion_keeps_structured_terminal_failure(self) -> None:
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                json={"title": "Self correction budget"},
            ).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "budget blocks repair",
                    "idempotencyKey": "self-correction-budget-exhausted",
                    "toolName": "repairable_5xx_tool",
                    "toolInput": {
                        "caseId": "bad",
                        "_selfCorrection": {"retryToolInput": {"caseId": "good"}},
                    },
                    "approvalMode": "always_approve",
                    "aiAssistantBudget": {"maxToolRepairAttempts": 0},
                },
            )
            run_id = turn.json()["data"].get("runId") if turn.status_code == 200 else None
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events") if run_id else None

        self.assertEqual(turn.status_code, 200, turn.text)
        data = turn.json()["data"]
        self.assertEqual(data["status"], "FAILED")
        self.assertEqual(data["toolCalls"][0]["output"]["observation"]["kind"], "tool_error")
        event_types = [event["type"] for event in events.json()["data"]["list"]]
        self.assertIn("tool.self_correction_exhausted", event_types)
        self.assertIn("run.failed", event_types)
        self.assertNotIn("tool.self_correction_completed", event_types)

    def test_timeout_observation_is_model_visible_and_can_degrade_within_budget(self) -> None:
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                json={"title": "Self correction timeout"},
            ).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "degrade after timeout",
                    "idempotencyKey": "self-correction-timeout-degrade",
                    "toolName": "timeout_tool",
                    "toolInput": {"caseId": "slow"},
                    "approvalMode": "always_approve",
                    "aiAssistantBudget": {"maxToolRepairAttempts": 1},
                },
            )
            run_id = turn.json()["data"].get("runId") if turn.status_code == 200 else None
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events") if run_id else None

        self.assertEqual(turn.status_code, 200, turn.text)
        data = turn.json()["data"]
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["toolCalls"][0]["output"]["observation"]["error"]["code"], "TOOL_TIMEOUT")
        self.assertIn("降级", data["finalAnswer"])
        event_types = [event["type"] for event in events.json()["data"]["list"]]
        self.assertIn("tool.self_correction_degraded", event_types)
        self.assertIn("run.completed", event_types)

    def _service_override(self) -> Generator[AiAssistantHarnessService, None, None]:
        with self._factory() as session:
            yield AiAssistantHarnessService(
                AiAssistantRepository(session),
                tool_registry=ToolRegistry(
                    {
                        "repairable_5xx_tool": (_read_manifest("repairable_5xx_tool"), self._repairable_5xx_tool),
                        "rate_limited_tool": (_read_manifest("rate_limited_tool"), self._rate_limited_tool),
                        "fallback_lookup_tool": (_read_manifest("fallback_lookup_tool"), self._fallback_lookup_tool),
                        "timeout_tool": (_read_manifest("timeout_tool", timeout_ms=5), self._timeout_tool),
                    }
                ),
            )

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session

    def _repairable_5xx_tool(self, payload: dict[str, Any]) -> ToolResult:
        self._calls.append({"toolName": "repairable_5xx_tool", "caseId": payload.get("caseId")})
        if payload.get("caseId") == "good":
            return ToolResult(status="COMPLETED", output={"status": "repaired", "caseId": "good"})
        raise RuntimeError("simulated 5xx")

    def _rate_limited_tool(self, payload: dict[str, Any]) -> ToolResult:
        self._calls.append({"toolName": "rate_limited_tool", "caseId": payload.get("caseId")})
        raise RuntimeError("rate limit exceeded")

    def _fallback_lookup_tool(self, payload: dict[str, Any]) -> ToolResult:
        self._calls.append({"toolName": "fallback_lookup_tool", "caseId": payload.get("caseId")})
        return ToolResult(status="COMPLETED", output={"status": "fallback", "caseId": payload.get("caseId")})

    def _timeout_tool(self, payload: dict[str, Any]) -> ToolResult:
        self._calls.append({"toolName": "timeout_tool", "caseId": payload.get("caseId")})
        time.sleep(0.05)
        return ToolResult(status="COMPLETED", output={"status": "late"})


def _read_manifest(name: str, *, timeout_ms: int = 50) -> ToolManifest:
    return ToolManifest(
        name=name,
        description=f"{name} test tool",
        input_schema={"type": "object", "properties": {"caseId": {"type": "string"}}},
        output_schema={"type": "object"},
        timeout_ms=timeout_ms,
        risk_level=RiskLevel.READ,
        read_resources=[],
        write_resources=[],
        policy_ref="ai_assistant_read_only",
    )


if __name__ == "__main__":
    unittest.main()
