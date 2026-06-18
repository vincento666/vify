from __future__ import annotations

from typing import Any


def build_observability_snapshot(
    *,
    run: dict[str, Any],
    events: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
) -> dict[str, Any]:
    usage = _usage_payload(run, events)
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


def _usage_payload(run: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    started_at = run.get("started_at")
    ended_at = run.get("completed_at") or run.get("updated_at")
    elapsed_ms = 0
    if started_at is not None and ended_at is not None:
        elapsed_ms = max(0, int((ended_at - started_at).total_seconds() * 1000))
    model_usage = _usage_from_run(run) or _usage_from_events(events)
    if model_usage is not None:
        return {
            **model_usage,
            "elapsedMs": elapsed_ms,
            "estimated": False,
        }
    return {
        "inputTokens": 0,
        "outputTokens": 0,
        "totalTokens": 0,
        "elapsedMs": elapsed_ms,
        "estimated": True,
    }


def _usage_from_run(run: dict[str, Any]) -> dict[str, int] | None:
    response = run.get("response_payload")
    if not isinstance(response, dict):
        return None
    model = response.get("model")
    if not isinstance(model, dict):
        return None
    return _normalize_usage(model.get("usage"))


def _usage_from_events(events: list[dict[str, Any]]) -> dict[str, int] | None:
    for event in reversed(events):
        if event.get("type") not in {"model.call_completed", "model.tool_call_decision"}:
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        normalized = _normalize_usage(payload.get("usage"))
        if normalized is not None:
            return normalized
    return None


def _normalize_usage(raw: Any) -> dict[str, int] | None:
    if not isinstance(raw, dict):
        return None
    input_tokens = _usage_number(raw, "inputTokens", "input_tokens", "prompt_tokens", "promptTokens")
    output_tokens = _usage_number(raw, "outputTokens", "output_tokens", "completion_tokens", "completionTokens")
    total_tokens = _usage_number(raw, "totalTokens", "total_tokens", "totalTokens")
    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens
    if input_tokens == 0 and output_tokens == 0 and total_tokens == 0:
        return None
    return {
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": total_tokens,
    }


def _usage_number(raw: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            return max(0, int(value))
        if isinstance(value, str) and value.strip().isdigit():
            return int(value)
    return 0
