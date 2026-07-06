import importlib
import importlib.util
import unittest
from datetime import datetime, timedelta
from typing import Any


class TraceAuditEvalBudgetTest(unittest.TestCase):
    def test_export_covers_trace_audit_budget_and_eval_surfaces(self) -> None:
        spec = importlib.util.find_spec("app.modules.ai_assistant.domain.trace_audit")
        self.assertIsNotNone(spec, "TraceAuditEvalBudget requires a trace_audit domain module")
        trace_audit = importlib.import_module("app.modules.ai_assistant.domain.trace_audit")

        export = trace_audit.build_trace_audit_export(
            run=_run(),
            events=_events(),
            tool_calls=_tool_calls(),
            approvals=_approvals(),
        )

        span_kinds = {span["kind"] for span in export["trace"]["spans"]}
        self.assertTrue(
            {
                "run",
                "model",
                "tool",
                "approval",
                "stream",
                "retry",
                "fallback",
                "skill",
                "file_edit",
                "resource_lock",
                "context_budget",
                "business_adapter",
            }.issubset(span_kinds)
        )
        self.assertEqual(export["audit"]["prompt"]["layers"][0]["name"], "AGENTS.md")
        self.assertEqual(export["audit"]["plan"]["id"], "plan-501")
        self.assertEqual(export["audit"]["toolCalls"][0]["toolName"], "mock_aviation.refund")
        self.assertEqual(export["audit"]["toolCalls"][0]["args"]["caseId"], "case-501")
        self.assertEqual(export["audit"]["toolCalls"][0]["result"]["status"], "MOCK_ACCEPTED")
        self.assertEqual(export["audit"]["retries"][0]["toolName"], "mock_aviation.refund")
        self.assertEqual(export["audit"]["fallbacks"][0]["type"], "tool.fallback_used")
        self.assertEqual(export["audit"]["approvals"][0]["status"], "APPROVED")
        self.assertEqual(export["audit"]["fileDiffs"][0]["toolName"], "mock_aviation.refund")
        self.assertEqual(export["audit"]["adapterAudits"][0]["adapterName"], "mock_aviation")
        self.assertEqual(export["audit"]["finalResult"], "Mock accepted.")
        self.assertEqual(export["budget"]["token"]["totalTokens"], 42)
        self.assertEqual(export["budget"]["tool"]["costUnits"], 2)
        self.assertTrue(export["eval"]["passed"])

    def test_budget_policy_degrades_when_tokens_or_cost_exceed_limits(self) -> None:
        spec = importlib.util.find_spec("app.modules.ai_assistant.domain.trace_audit")
        self.assertIsNotNone(spec, "TraceAuditEvalBudget requires a trace_audit domain module")
        trace_audit = importlib.import_module("app.modules.ai_assistant.domain.trace_audit")

        decision = trace_audit.evaluate_budget_policy(
            usage={"inputTokens": 900, "outputTokens": 150, "totalTokens": 1050},
            cost={"estimatedUsd": 1.25, "maxUsd": 1.0},
            model_policy={"primaryModel": "qwen-max", "fallbackModel": "qwen-turbo"},
            max_tokens=1000,
        )

        self.assertEqual(decision["status"], "over_budget")
        self.assertEqual(decision["model"]["action"], "degrade")
        self.assertEqual(decision["model"]["selectedModel"], "qwen-turbo")
        self.assertIn("token_budget_exceeded", decision["reasons"])
        self.assertIn("cost_budget_exceeded", decision["reasons"])

    def test_eval_report_fails_when_required_trace_or_audit_coverage_is_missing(self) -> None:
        spec = importlib.util.find_spec("app.modules.ai_assistant.domain.trace_audit")
        self.assertIsNotNone(spec, "TraceAuditEvalBudget requires a trace_audit domain module")
        trace_audit = importlib.import_module("app.modules.ai_assistant.domain.trace_audit")

        report = trace_audit.build_trace_eval_report(
            {
                "trace": {"spans": [{"kind": "run"}, {"kind": "tool"}, {"kind": "context_budget"}]},
                "audit": {
                    "prompt": {"message": "partial"},
                    "plan": {"id": "plan-partial"},
                    "toolCalls": [{"toolName": "echo_context"}],
                    "finalResult": "partial",
                },
                "budget": {
                    "token": {"totalTokens": 1},
                    "cost": {"estimatedUsd": 0.0},
                    "policy": {"model": {"action": "continue"}},
                },
            }
        )

        self.assertFalse(report["passed"])
        checks = {check["id"]: check for check in report["checks"]}
        self.assertFalse(checks["trace_coverage"]["passed"])
        self.assertIn("approval", checks["trace_coverage"]["missingSpanKinds"])
        self.assertFalse(checks["audit_export_completeness"]["passed"])
        self.assertIn("adapterAudits", checks["audit_export_completeness"]["missingAuditFields"])

    def test_budget_record_uses_persisted_run_limits_and_model_policy(self) -> None:
        spec = importlib.util.find_spec("app.modules.ai_assistant.domain.trace_audit")
        self.assertIsNotNone(spec, "TraceAuditEvalBudget requires a trace_audit domain module")
        trace_audit = importlib.import_module("app.modules.ai_assistant.domain.trace_audit")

        run = _run()
        run["input_payload"] = {
            **run["input_payload"],
            "aiAssistantBudget": {"maxTokens": 40, "maxUsd": 0.000001},
            "modelBudgetPolicy": {"primaryModel": "qwen-max", "fallbackModel": "qwen-turbo"},
        }
        export = trace_audit.build_trace_audit_export(
            run=run,
            events=_events(),
            tool_calls=_tool_calls(),
            approvals=_approvals(),
        )

        self.assertEqual(export["budget"]["cost"]["maxUsd"], 0.000001)
        self.assertEqual(export["budget"]["token"]["maxTokens"], 40)
        self.assertEqual(export["budget"]["policy"]["status"], "over_budget")
        self.assertEqual(export["budget"]["policy"]["model"]["action"], "degrade")
        self.assertEqual(export["budget"]["policy"]["model"]["selectedModel"], "qwen-turbo")
        self.assertIn("token_budget_exceeded", export["budget"]["policy"]["reasons"])
        self.assertIn("cost_budget_exceeded", export["budget"]["policy"]["reasons"])


def _run() -> dict[str, Any]:
    started = datetime(2026, 7, 4, 12, 0, 0)
    return {
        "id": 501,
        "session_id": 7,
        "status": "COMPLETED",
        "input_payload": {
            "message": "mock refund",
            "plan": {"id": "plan-501", "planningStrategy": "deliberate"},
            "contextBudget": _context_budget(),
        },
        "response_payload": {
            "finalAnswer": "Mock accepted.",
            "plan": {"id": "plan-501", "planningStrategy": "deliberate", "status": "COMPLETED"},
            "model": {"usage": {"inputTokens": 30, "outputTokens": 12, "totalTokens": 42}},
        },
        "started_at": started,
        "updated_at": started + timedelta(milliseconds=250),
        "completed_at": started + timedelta(milliseconds=250),
    }


def _events() -> list[dict[str, Any]]:
    base = datetime(2026, 7, 4, 12, 0, 0)
    event_specs = [
        ("run.started", {"phase": "reason"}),
        ("plan.created", {"plan": {"id": "plan-501", "planningStrategy": "deliberate"}}),
        ("context.budget_estimated", {"contextBudget": _context_budget()}),
        ("context.compaction_completed", {"summaryHash": "sum-501"}),
        ("model.call_started", {"model": "qwen-max"}),
        ("text.delta", {"delta": "Mock"}),
        ("stream.fallback", {"model": "qwen-max", "fallback": True, "source": "post_completion_split"}),
        ("model.call_completed", {"model": "qwen-max", "usage": {"inputTokens": 30, "outputTokens": 12}}),
        ("approval.required", {"approvalId": 3, "toolName": "mock_aviation.refund"}),
        ("approval.granted", {"approvalId": 3, "actorId": "operator"}),
        ("resource_lock.acquired", {"resourceKey": "business_adapter:mock_aviation.refund", "mode": "WRITE"}),
        ("tool.call_started", {"toolName": "mock_aviation.refund"}),
        ("tool.retry_scheduled", {"toolName": "mock_aviation.refund", "attempt": 1}),
        ("tool.fallback_used", {"toolName": "mock_aviation.refund", "status": "COMPLETED"}),
        ("skill.loaded", {"skillName": "refund-helper", "checksum": "abc"}),
        ("tool.call_completed", {"toolName": "mock_aviation.refund", "status": "COMPLETED"}),
        ("resource_lock.released", {"resourceKey": "business_adapter:mock_aviation.refund", "mode": "WRITE"}),
        ("run.completed", {"finalAnswer": "Mock accepted."}),
    ]
    return [
        {
            "id": index,
            "session_id": 7,
            "run_id": 501,
            "task_id": None,
            "tool_call_id": 9 if "tool" in event_type or "skill" in event_type else None,
            "sequence": index,
            "type": event_type,
            "level": "info",
            "status": "COMPLETED",
            "visible_title": event_type,
            "visible_summary": event_type,
            "payload": payload,
            "correlation_ids": {},
            "created_at": base + timedelta(milliseconds=index * 5),
        }
        for index, (event_type, payload) in enumerate(event_specs, start=1)
    ]


def _tool_calls() -> list[dict[str, Any]]:
    now = datetime(2026, 7, 4, 12, 0, 0)
    return [
        {
            "id": 9,
            "session_id": 7,
            "run_id": 501,
            "tool_name": "mock_aviation.refund",
            "input_payload": {
                "caseId": "case-501",
                "passengerId": "PAX-501",
                "_toolRuntime": {
                    "idempotencyKey": "mock_aviation.refund:case-501",
                    "attempts": 2,
                    "span": {"toolName": "mock_aviation.refund", "status": "OK"},
                    "budget": {"attempts": 2, "retries": 1, "durationMs": 35, "costUnits": 2},
                },
            },
            "output_payload": {
                "status": "MOCK_ACCEPTED",
                "diffPreview": "--- a/mock\n+++ b/mock\n@@\n-old\n+new",
                "audit": {
                    "adapterName": "mock_aviation",
                    "toolName": "mock_aviation.refund",
                    "mockOnly": True,
                    "realAviationRulesApplied": False,
                },
                "compensationTransaction": {"status": "MOCK_COMPENSATION_READY"},
            },
            "status": "COMPLETED",
            "duration_ms": 35,
            "started_at": now,
            "completed_at": now + timedelta(milliseconds=35),
        }
    ]


def _approvals() -> list[dict[str, Any]]:
    return [
        {
            "id": 3,
            "session_id": 7,
            "run_id": 501,
            "tool_name": "mock_aviation.refund",
            "risk_level": "BUSINESS_WRITE",
            "input_payload": {"caseId": "case-501"},
            "status": "APPROVED",
            "decided_by": "operator",
            "decision_reason": "",
        }
    ]


def _context_budget() -> dict[str, Any]:
    return {
        "usage": {"usedTokens": 150, "maxTokens": 128000, "usagePercent": 0.12},
        "selectedLayers": [{"name": "AGENTS.md", "tokens": 40, "sharePercent": 26.7}],
        "droppedLayers": [{"name": "old_tool_output", "tokens": 900, "reason": "context_window_budget"}],
        "dropReasons": [{"name": "old_tool_output", "reason": "context_window_budget"}],
        "compactionSnapshot": {
            "algorithm": "deterministic-context-budget-v1",
            "summaryHash": "sum-501",
            "sourceMessageIds": [1, 2],
            "sourceEventIds": [1, 2, 3],
            "rawTokens": 1000,
            "summaryTokens": 120,
            "compressionRatio": 88,
        },
    }


if __name__ == "__main__":
    unittest.main()
