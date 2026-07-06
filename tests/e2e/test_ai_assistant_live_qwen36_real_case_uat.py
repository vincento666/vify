import json
import os
import unittest
from collections.abc import Generator
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.live_model import LivePlannerConfig, QwenLivePlanner
from app.modules.ai_assistant.web.router import get_ai_assistant_service
from tests.support.ai_assistant_memory_repo import InMemoryAiAssistantRepository


LIVE_MODEL = "qwen/qwen3.6-27b"


@unittest.skipUnless(
    os.getenv("HIFY_RUN_LIVE_AI_ASSISTANT") == "1" and os.getenv("OPENROUTER_API_KEY"),
    "HIFY_RUN_LIVE_AI_ASSISTANT=1 and OPENROUTER_API_KEY are required for live OpenRouter UAT",
)
class AiAssistantLiveQwen36RealCaseUatTest(unittest.TestCase):
    def setUp(self) -> None:
        self._repository = InMemoryAiAssistantRepository()
        app.dependency_overrides[get_ai_assistant_service] = self._service_override

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_ai_assistant_service, None)

    def test_qwen36_streams_real_tokens_and_exports_redacted_audit_budget(self) -> None:
        client = TestClient(app)
        try:
            session_id = self._create_session(client, "222.11 qwen3.6 stream UAT")
            turn = self._send_live_message(
                client,
                session_id,
                "请用一句中文回复 HIFY_LIVE_QWEN36_STREAM_OK，不要调用任何工具。",
                "live-qwen36-stream",
                max_tokens=120,
            )
            run_id = int(turn["runId"])
            events = self._events(client, run_id)
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{run_id}/snapshot", params={"afterSequence": 1})
            audit = client.get(f"/api/v1/ai-assistant/runs/{run_id}/audit").json()["data"]
        finally:
            client.close()

        self.assertEqual(turn["status"], "COMPLETED")
        stream_events = [
            event
            for event in events
            if event["type"] == "model.stream_chunk"
            and event["payload"].get("source") == "openrouter_delta"
            and event["payload"].get("streaming") is True
        ]
        self.assertTrue(stream_events, "qwen3.6 must produce raw provider stream chunks for plain text output")
        first_stream_sequence = min(event["sequence"] for event in stream_events)
        completed_sequence = next(event["sequence"] for event in events if event["type"] == "model.call_completed")
        self.assertLess(first_stream_sequence, completed_sequence)
        self.assertGreater(snapshot.json()["data"]["streamCursor"]["lastSequence"], first_stream_sequence)
        self.assertEqual(audit["budget"]["policy"]["status"], "within_budget")
        self.assertGreater(audit["budget"]["token"]["totalTokens"], 0)
        self.assertGreater(audit["budget"]["cost"]["estimatedUsd"], 0)
        self.assertGreater(audit["audit"]["contextBudget"]["usage"]["maxTokens"], 0)
        self.assertNotIn("sk-or-v1", json.dumps(audit, ensure_ascii=False))
        print(
            json.dumps(
                {
                    "case": "stream",
                    "runId": run_id,
                    "model": LIVE_MODEL,
                    "rawStreamChunks": len(stream_events),
                    "firstStreamBeforeCompletion": first_stream_sequence < completed_sequence,
                    "totalTokens": audit["budget"]["token"]["totalTokens"],
                    "contextMaxTokens": audit["audit"]["contextBudget"]["usage"]["maxTokens"],
                },
                ensure_ascii=False,
            )
        )

    def test_qwen36_executes_realistic_cases_through_mock_aviation_adapter_seam(self) -> None:
        scenarios = [
            ("refund", "mock_aviation.refund", True),
            ("change_ticket", "mock_aviation.change_ticket", True),
            ("baggage", "mock_aviation.baggage", False),
            ("flight_disruption", "mock_aviation.flight_disruption", False),
        ]
        client = TestClient(app)
        summaries: list[dict[str, Any]] = []
        try:
            for scenario, tool_name, requires_approval in scenarios:
                session_id = self._create_session(client, f"222.11 {scenario} UAT")
                turn = self._send_live_message(
                    client,
                    session_id,
                    self._case_prompt(scenario, tool_name),
                    f"live-qwen36-{scenario}",
                    max_tokens=220,
                )
                if requires_approval:
                    self.assertEqual(turn["status"], "WAITING_APPROVAL")
                    self.assertTrue(turn["approvalRequired"])
                    approve = client.post(
                        f"/api/v1/ai-assistant/approvals/{turn['approvalId']}/approve",
                        json={"actorId": "live-uat"},
                    )
                    self.assertEqual(approve.status_code, 200, approve.text)
                else:
                    self.assertEqual(turn["status"], "COMPLETED")
                    self.assertFalse(turn["approvalRequired"])

                run_id = int(turn["runId"])
                result = client.get(f"/api/v1/ai-assistant/runs/{run_id}/result").json()["data"]
                events = self._events(client, run_id)
                audit = client.get(f"/api/v1/ai-assistant/runs/{run_id}/audit").json()["data"]
                tool_calls = result["toolCalls"]
                matching = [call for call in tool_calls if call["toolName"] == tool_name]

                self.assertTrue(matching, f"{scenario} must call {tool_name}")
                output = matching[-1]["output"]
                self.assertEqual(output["businessEffect"], "mock_only")
                self.assertEqual(output["audit"]["adapterName"], "mock_aviation")
                self.assertTrue(output["audit"]["mockOnly"])
                self.assertFalse(output["audit"]["realAviationRulesApplied"])
                self.assertIn("idempotencyKey", output)
                self.assertEqual(output["compensationTransaction"]["status"], "MOCK_COMPENSATION_READY")
                self.assertTrue(any(event["type"] == "model.tool_call_decision" for event in events))
                self.assertTrue(any(event["type"] == "context.budget_estimated" for event in events))
                if requires_approval:
                    self.assertTrue(any(event["type"] == "approval.required" for event in events))
                    self.assertTrue(any(event["type"] == "approval.granted" for event in events))
                self.assertTrue(audit["audit"]["adapterAudits"])
                self.assertGreaterEqual(audit["budget"]["tool"]["attempts"], 1)
                self.assertNotIn("sk-or-v1", json.dumps(audit, ensure_ascii=False))
                summaries.append(
                    {
                        "case": scenario,
                        "runId": run_id,
                        "model": LIVE_MODEL,
                        "status": result["status"],
                        "toolName": tool_name,
                        "approvalRequired": requires_approval,
                        "idempotencyKey": output["idempotencyKey"],
                        "compensationStatus": output["compensationTransaction"]["status"],
                        "adapterAuditMockOnly": output["audit"]["mockOnly"],
                        "totalTokens": audit["budget"]["token"]["totalTokens"],
                        "toolAttempts": audit["budget"]["tool"]["attempts"],
                    }
                )
        finally:
            client.close()

        print(json.dumps({"cases": summaries}, ensure_ascii=False))

    def _service_override(self) -> Generator[AiAssistantHarnessService, None, None]:
        yield AiAssistantHarnessService(
            self._repository,
            live_planner=QwenLivePlanner(
                LivePlannerConfig(
                    base_url="https://openrouter.ai/api/v1",
                    model=LIVE_MODEL,
                    api_key_ref="env:OPENROUTER_API_KEY",
                    provider="openrouter",
                    temperature=0,
                    max_tokens=220,
                ),
            ),
        )

    def _create_session(self, client: TestClient, title: str) -> int:
        response = client.post("/api/v1/ai-assistant/sessions", json={"title": title})
        self.assertEqual(response.status_code, 200, response.text)
        return int(response.json()["data"]["id"])

    def _send_live_message(
        self,
        client: TestClient,
        session_id: int,
        message: str,
        idempotency_key: str,
        *,
        max_tokens: int,
    ) -> dict[str, Any]:
        response = client.post(
            f"/api/v1/ai-assistant/sessions/{session_id}/messages",
            json={
                "message": message,
                "idempotencyKey": idempotency_key,
                "modelMode": "live",
                "approvalMode": "smart_approval",
                "modelConfig": {
                    "provider": "openrouter",
                    "baseUrl": "https://openrouter.ai/api/v1",
                    "model": LIVE_MODEL,
                    "apiKeyRef": "env:OPENROUTER_API_KEY",
                    "temperature": 0,
                    "maxTokens": max_tokens,
                },
                "aiAssistantBudget": {"maxTokens": 20000, "maxUsd": 0.05},
                "modelBudgetPolicy": {"primaryModel": LIVE_MODEL, "fallbackModel": LIVE_MODEL},
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]

    def _events(self, client: TestClient, run_id: int) -> list[dict[str, Any]]:
        response = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events")
        self.assertEqual(response.status_code, 200, response.text)
        return list(response.json()["data"]["list"])

    def _case_prompt(self, scenario: str, tool_name: str) -> str:
        payload = {
            "caseId": f"live-{scenario}",
            "passengerId": f"PAX-LIVE-{scenario.upper()}",
            "request": f"{scenario} mock aviation real-case UAT",
        }
        return (
            f"这是 Spec 222.11 live qwen3.6 真实案例 UAT。必须调用 function tool {tool_name}，"
            f"不要只用文字回答。工具参数必须完全使用这个 JSON: {json.dumps(payload, ensure_ascii=False)}。"
            "执行后请用中文简短说明 mock adapter 返回的状态、idempotencyKey、compensation 和 audit 事实。"
        )


if __name__ == "__main__":
    unittest.main()
