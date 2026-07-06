from app.modules.ai_assistant.domain.trace_audit import build_trace_eval_report


def test_trace_audit_eval_requires_trace_audit_budget_and_model_policy() -> None:
    report = build_trace_eval_report(
        {
            "trace": {
                "spans": [
                    {"kind": "run"},
                    {"kind": "model"},
                    {"kind": "tool"},
                    {"kind": "approval"},
                    {"kind": "stream"},
                    {"kind": "retry"},
                    {"kind": "fallback"},
                    {"kind": "skill"},
                    {"kind": "file_edit"},
                    {"kind": "resource_lock"},
                    {"kind": "context_budget"},
                    {"kind": "business_adapter"},
                ]
            },
            "audit": {
                "prompt": {
                    "message": "hello",
                    "layers": [{"name": "AGENTS.md"}],
                    "contextBudget": {"usage": {"usedTokens": 1}},
                    "compactionSnapshot": {"summaryHash": "hash"},
                },
                "plan": {"id": "plan-1"},
                "toolCalls": [{"toolName": "echo_context"}],
                "retries": [{"toolName": "echo_context"}],
                "fallbacks": [{"toolName": "echo_context"}],
                "approvals": [{"status": "APPROVED"}],
                "tokenCost": {"token": {"totalTokens": 1}, "cost": {"estimatedUsd": 0.0}},
                "fileDiffs": [{"diffPreview": "---"}],
                "adapterAudits": [{"adapterName": "mock_aviation"}],
                "contextBudget": {"usage": {"usedTokens": 1}},
                "compactionSnapshot": {"summaryHash": "hash"},
                "finalResult": "done",
            },
            "budget": {
                "token": {"totalTokens": 1},
                "cost": {"estimatedUsd": 0.0},
                "policy": {"model": {"action": "continue"}},
            },
        }
    )

    assert report["passed"] is True
    assert [check["id"] for check in report["checks"]] == [
        "trace_coverage",
        "audit_export_completeness",
        "budget_records",
        "model_degradation_policy",
    ]


def test_trace_audit_eval_fails_when_required_coverage_is_missing() -> None:
    report = build_trace_eval_report(
        {
            "trace": {"spans": [{"kind": "run"}, {"kind": "tool"}]},
            "audit": {
                "prompt": {"message": "partial"},
                "plan": {"id": "plan-1"},
                "toolCalls": [{"toolName": "echo_context"}],
                "finalResult": "done",
            },
            "budget": {
                "token": {"totalTokens": 1},
                "cost": {"estimatedUsd": 0.0},
                "policy": {"model": {"action": "continue"}},
            },
        }
    )

    assert report["passed"] is False
    checks = {check["id"]: check for check in report["checks"]}
    assert "approval" in checks["trace_coverage"]["missingSpanKinds"]
    assert "adapterAudits" in checks["audit_export_completeness"]["missingAuditFields"]
