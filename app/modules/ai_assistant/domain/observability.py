from __future__ import annotations

from typing import Any


def build_observability_snapshot(
    *,
    run: dict[str, Any],
    events: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
) -> dict[str, Any]:
    usage = _usage_payload(run)
    benchmark = {
        "name": "ai_assistant_deterministic_mvp",
        "passed": run.get("status") in {"COMPLETED", "WAITING_APPROVAL", "DENIED"},
        "metrics": {
            "elapsedMs": usage["elapsedMs"],
            "eventCount": len(events),
            "toolCallCount": len(tool_calls),
            "approvalCount": len(approvals),
        },
        "thresholds": {
            "maxElapsedMs": 5000,
            "minEventCount": 1,
        },
    }
    return {
        "runId": run["id"],
        "status": run["status"],
        "eventCount": len(events),
        "toolCallCount": len(tool_calls),
        "approvalCount": len(approvals),
        "usage": usage,
        "benchmark": benchmark,
    }


def _usage_payload(run: dict[str, Any]) -> dict[str, Any]:
    started_at = run.get("started_at")
    ended_at = run.get("completed_at") or run.get("updated_at")
    elapsed_ms = 0
    if started_at is not None and ended_at is not None:
        elapsed_ms = max(0, int((ended_at - started_at).total_seconds() * 1000))
    return {
        "inputTokens": 0,
        "outputTokens": 0,
        "totalTokens": 0,
        "elapsedMs": elapsed_ms,
        "estimated": True,
    }
