from __future__ import annotations

from datetime import datetime
from typing import Any


TRACE_REQUIRED_KINDS = {
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
}

AUDIT_REQUIRED_FIELDS = {
    "prompt.layers",
    "prompt.contextBudget",
    "prompt.compactionSnapshot",
    "plan",
    "toolCalls",
    "retries",
    "fallbacks",
    "approvals",
    "tokenCost",
    "fileDiffs",
    "adapterAudits",
    "contextBudget",
    "compactionSnapshot",
    "finalResult",
}


def build_trace_audit_export(
    *,
    run: dict[str, Any],
    events: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    durable_tool_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_id = int(run["id"])
    budget = build_budget_record(run=run, events=events, tool_calls=tool_calls)
    export = {
        "runId": run_id,
        "sessionId": int(run["session_id"]),
        "status": str(run["status"]),
        "trace": {"runId": run_id, "spans": build_trace_spans(run=run, events=events, tool_calls=tool_calls, approvals=approvals)},
        "audit": build_audit_record(
            run=run,
            events=events,
            tool_calls=tool_calls,
            approvals=approvals,
            budget=budget,
            durable_tool_ledger=durable_tool_ledger or {},
        ),
        "budget": budget,
    }
    export["eval"] = build_trace_eval_report(export)
    return export


def build_trace_spans(
    *,
    run: dict[str, Any],
    events: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = [
        {
            "spanId": f"run-{run['id']}",
            "parentSpanId": None,
            "kind": "run",
            "name": f"ai_assistant.run.{run['status']}",
            "status": str(run["status"]),
            "startedAt": _iso(run.get("started_at")),
            "endedAt": _iso(run.get("completed_at") or run.get("updated_at")),
            "durationMs": _duration_ms(run.get("started_at"), run.get("completed_at") or run.get("updated_at")),
            "attributes": {"sessionId": run["session_id"], "runId": run["id"]},
        }
    ]
    spans.extend(_event_spans(run_id=int(run["id"]), events=events))
    spans.extend(_tool_spans(run_id=int(run["id"]), tool_calls=tool_calls))
    spans.extend(_approval_spans(run_id=int(run["id"]), approvals=approvals))
    return _dedupe_spans(spans)


def build_audit_record(
    *,
    run: dict[str, Any],
    events: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    budget: dict[str, Any],
    durable_tool_ledger: dict[str, Any],
) -> dict[str, Any]:
    input_payload = _dict(run.get("input_payload"))
    response_payload = _dict(run.get("response_payload"))
    context_budget = _context_budget(run, events)
    return {
        "prompt": {
            "message": str(input_payload.get("message") or ""),
            "layers": _prompt_layers(context_budget),
            "contextBudget": context_budget,
            "compactionSnapshot": _compaction_snapshot(run, events, context_budget),
        },
        "plan": _plan_payload(run),
        "toolCalls": [_audit_tool_call(row) for row in tool_calls],
        "retries": _events_of_type(
            events,
            {
                "tool.retry_scheduled",
                "tool.self_correction_started",
                "tool.self_correction_completed",
                "tool.self_correction_exhausted",
            },
        ),
        "fallbacks": _events_of_type(
            events,
            {"tool.fallback_used", "stream.fallback", "tool.self_correction_fallback_selected", "tool.self_correction_degraded"},
        ),
        "selfCorrections": _events_of_type(
            events,
            {
                "tool.self_correction_started",
                "tool.self_correction_fallback_selected",
                "tool.self_correction_completed",
                "tool.self_correction_degraded",
                "tool.self_correction_exhausted",
                "tool.self_correction_terminal",
            },
        ),
        "approvals": [_audit_approval(row) for row in approvals],
        "tokenCost": {"token": budget["token"], "cost": budget["cost"]},
        "fileDiffs": _file_diffs(tool_calls),
        "adapterAudits": _adapter_audits(tool_calls),
        "contextBudget": context_budget,
        "compactionSnapshot": _compaction_snapshot(run, events, context_budget),
        "finalResult": str(response_payload.get("finalAnswer") or ""),
        "durableToolLedger": {
            "operations": _list(durable_tool_ledger.get("operations")),
            "attempts": _list(durable_tool_ledger.get("attempts")),
            "releases": _list(durable_tool_ledger.get("releases")),
            "breakers": _list(durable_tool_ledger.get("breakers")),
        },
    }


def build_budget_record(
    *,
    run: dict[str, Any],
    events: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    token_usage = _token_usage(run, events)
    tool_budget = _tool_budget(tool_calls)
    cost = {
        "estimatedUsd": round(float(token_usage["totalTokens"]) * 0.000001 + float(tool_budget["costUnits"]) * 0.00001, 6),
        "modelEstimatedUsd": round(float(token_usage["totalTokens"]) * 0.000001, 6),
        "toolEstimatedUsd": round(float(tool_budget["costUnits"]) * 0.00001, 6),
    }
    input_payload = _dict(run.get("input_payload"))
    max_tokens = _budget_max_tokens(input_payload, token_usage)
    max_usd = _budget_max_usd(input_payload)
    token_usage = dict(token_usage) | {"maxTokens": max_tokens}
    if max_usd is not None:
        cost["maxUsd"] = max_usd
    context = _dict(input_payload.get("contextBudget"))
    policy = evaluate_budget_policy(
        usage=token_usage,
        cost=cost,
        model_policy=_dict(input_payload.get("modelBudgetPolicy")),
        max_tokens=max_tokens,
    )
    return {
        "token": token_usage,
        "cost": cost,
        "tool": tool_budget,
        "context": context,
        "policy": policy,
    }


def evaluate_budget_policy(
    *,
    usage: dict[str, Any],
    cost: dict[str, Any],
    model_policy: dict[str, Any],
    max_tokens: int,
) -> dict[str, Any]:
    total_tokens = _int_from(usage, "totalTokens")
    estimated_usd = _float_from(cost, "estimatedUsd")
    max_usd = _float_from(cost, "maxUsd")
    reasons: list[str] = []
    if total_tokens > max(0, int(max_tokens)):
        reasons.append("token_budget_exceeded")
    if max_usd > 0 and estimated_usd > max_usd:
        reasons.append("cost_budget_exceeded")
    primary_model = str(model_policy.get("primaryModel") or model_policy.get("primary_model") or "default")
    fallback_model = str(model_policy.get("fallbackModel") or model_policy.get("fallback_model") or primary_model)
    over_budget = bool(reasons)
    return {
        "status": "over_budget" if over_budget else "within_budget",
        "reasons": reasons,
        "model": {
            "primaryModel": primary_model,
            "fallbackModel": fallback_model,
            "selectedModel": fallback_model if over_budget and fallback_model else primary_model,
            "action": "degrade" if over_budget and fallback_model and fallback_model != primary_model else "continue",
        },
    }


def build_trace_eval_report(export: dict[str, Any]) -> dict[str, Any]:
    span_kinds = {str(span.get("kind")) for span in _list(_dict(export.get("trace")).get("spans"))}
    audit = _dict(export.get("audit"))
    budget = _dict(export.get("budget"))
    missing_span_kinds = sorted(TRACE_REQUIRED_KINDS - span_kinds)
    missing_audit_fields = _missing_audit_fields(audit)
    checks = [
        {
            "id": "trace_coverage",
            "passed": not missing_span_kinds,
            "observedKinds": sorted(span_kinds),
            "missingSpanKinds": missing_span_kinds,
        },
        {
            "id": "audit_export_completeness",
            "passed": not missing_audit_fields,
            "missingAuditFields": missing_audit_fields,
        },
        {
            "id": "budget_records",
            "passed": bool(budget.get("token")) and bool(budget.get("cost")) and bool(budget.get("policy")),
        },
        {
            "id": "model_degradation_policy",
            "passed": bool(_dict(budget.get("policy")).get("model")),
        },
    ]
    return {
        "name": "ai_assistant_trace_audit_budget_regression",
        "passed": all(bool(check["passed"]) for check in checks),
        "checks": checks,
    }


def _event_spans(*, run_id: int, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for event in events:
        event_type = str(event.get("type") or "")
        for kind in _event_kinds(event_type):
            spans.append(
                {
                    "spanId": f"{kind}-event-{event.get('id') or event.get('sequence')}",
                    "parentSpanId": f"run-{run_id}",
                    "kind": kind,
                    "name": event_type,
                    "status": str(event.get("status") or "COMPLETED"),
                    "startedAt": _iso(event.get("created_at")),
                    "endedAt": _iso(event.get("created_at")),
                    "durationMs": 0,
                    "attributes": _dict(event.get("payload")) | {"sequence": event.get("sequence")},
                }
            )
    return spans


def _tool_spans(*, run_id: int, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for row in tool_calls:
        tool_name = str(row.get("tool_name") or "")
        tool_id = row.get("id") or tool_name
        spans.append(
            {
                "spanId": f"tool-{tool_id}",
                "parentSpanId": f"run-{run_id}",
                "kind": "tool",
                "name": tool_name,
                "status": str(row.get("status") or ""),
                "startedAt": _iso(row.get("started_at")),
                "endedAt": _iso(row.get("completed_at")),
                "durationMs": int(row.get("duration_ms") or 0),
                "attributes": {
                    "toolName": tool_name,
                    "idempotencyKey": _dict(_dict(row.get("input_payload")).get("_toolRuntime")).get("idempotencyKey"),
                },
            }
        )
        output = _dict(row.get("output_payload"))
        if output.get("diffPreview") or output.get("rollbackSnapshot"):
            spans.append(_derived_tool_span(run_id, tool_id, "file_edit", tool_name, row))
        audit = _dict(output.get("audit"))
        if audit.get("adapterName"):
            spans.append(_derived_tool_span(run_id, tool_id, "business_adapter", str(audit.get("adapterName")), row))
    return spans


def _approval_spans(*, run_id: int, approvals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for approval in approvals:
        spans.append(
            {
                "spanId": f"approval-{approval.get('id')}",
                "parentSpanId": f"run-{run_id}",
                "kind": "approval",
                "name": str(approval.get("tool_name") or ""),
                "status": str(approval.get("status") or ""),
                "startedAt": _iso(approval.get("created_at")),
                "endedAt": _iso(approval.get("decided_at") or approval.get("updated_at")),
                "durationMs": _duration_ms(approval.get("created_at"), approval.get("decided_at") or approval.get("updated_at")),
                "attributes": {
                    "approvalId": approval.get("id"),
                    "riskLevel": approval.get("risk_level"),
                    "decidedBy": approval.get("decided_by"),
                },
            }
        )
    return spans


def _derived_tool_span(run_id: int, tool_id: Any, kind: str, name: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "spanId": f"{kind}-{tool_id}",
        "parentSpanId": f"tool-{tool_id}",
        "kind": kind,
        "name": name,
        "status": str(row.get("status") or ""),
        "startedAt": _iso(row.get("started_at")),
        "endedAt": _iso(row.get("completed_at")),
        "durationMs": int(row.get("duration_ms") or 0),
        "attributes": {"runId": run_id, "toolName": row.get("tool_name")},
    }


def _event_kinds(event_type: str) -> list[str]:
    kinds: list[str] = []
    if event_type.startswith("model."):
        kinds.append("model")
    if event_type in {"text.delta", "stream.fallback", "heartbeat"}:
        kinds.append("stream")
    if event_type == "tool.retry_scheduled":
        kinds.append("retry")
    if event_type.startswith("tool.self_correction"):
        kinds.append("retry")
    if event_type in {"tool.fallback_used", "stream.fallback"}:
        kinds.append("fallback")
    if event_type in {"tool.self_correction_fallback_selected", "tool.self_correction_degraded"}:
        kinds.append("fallback")
    if event_type.startswith("skill."):
        kinds.append("skill")
    if event_type.startswith("resource_lock."):
        kinds.append("resource_lock")
    if event_type.startswith("context."):
        kinds.append("context_budget")
    return kinds


def _dedupe_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for span in spans:
        span_id = str(span.get("spanId") or "")
        if span_id in seen:
            continue
        seen.add(span_id)
        result.append(span)
    return result


def _audit_tool_call(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "toolName": row.get("tool_name"),
        "status": row.get("status"),
        "durationMs": int(row.get("duration_ms") or 0),
        "args": _public_args(_dict(row.get("input_payload"))),
        "result": _dict(row.get("output_payload")),
        "runtime": _dict(_dict(row.get("input_payload")).get("_toolRuntime")),
    }


def _audit_approval(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "toolName": row.get("tool_name"),
        "riskLevel": row.get("risk_level"),
        "input": _dict(row.get("input_payload")),
        "status": row.get("status"),
        "decidedBy": row.get("decided_by"),
        "decisionReason": row.get("decision_reason") or "",
    }


def _events_of_type(events: list[dict[str, Any]], types: set[str]) -> list[dict[str, Any]]:
    rows = [
        {
            "id": event.get("id"),
            "sequence": event.get("sequence"),
            "type": event.get("type"),
            "toolName": _dict(event.get("payload")).get("toolName"),
            "payload": _dict(event.get("payload")),
        }
        for event in events
        if event.get("type") in types
    ]
    if "tool.fallback_used" in types:
        rows.sort(key=lambda item: (0 if item["type"] == "tool.fallback_used" else 1, _int_value(item.get("sequence"))))
    return rows


def _file_diffs(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    for row in tool_calls:
        output = _dict(row.get("output_payload"))
        diff_preview = output.get("diffPreview")
        if not diff_preview:
            continue
        diffs.append(
            {
                "toolCallId": row.get("id"),
                "toolName": row.get("tool_name"),
                "diffPreview": diff_preview,
                "rollbackSnapshot": output.get("rollbackSnapshot"),
                "checksum": output.get("checksum"),
            }
        )
    return diffs


def _adapter_audits(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    audits: list[dict[str, Any]] = []
    for row in tool_calls:
        audit = _dict(_dict(row.get("output_payload")).get("audit"))
        if audit.get("adapterName"):
            audits.append(dict(audit) | {"toolCallId": row.get("id")})
    return audits


def _tool_budget(tool_calls: list[dict[str, Any]]) -> dict[str, int]:
    attempts = 0
    retries = 0
    duration_ms = 0
    cost_units = 0
    for row in tool_calls:
        runtime = _dict(_dict(row.get("input_payload")).get("_toolRuntime"))
        budget = _dict(runtime.get("budget"))
        attempts += _int_from(budget, "attempts")
        retries += _int_from(budget, "retries")
        duration_ms += _int_from(budget, "durationMs", "duration_ms")
        cost_units += _int_from(budget, "costUnits", "cost_units")
    if tool_calls and cost_units == 0:
        cost_units = len(tool_calls)
    return {
        "attempts": attempts,
        "retries": retries,
        "durationMs": duration_ms,
        "costUnits": cost_units,
    }


def _token_usage(run: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, int]:
    response = _dict(run.get("response_payload"))
    model = _dict(response.get("model"))
    usage = _normalize_usage(model.get("usage"))
    if usage is not None:
        return usage
    for event in reversed(events):
        if event.get("type") not in {"model.call_completed", "model.tool_call_decision"}:
            continue
        usage = _normalize_usage(_dict(event.get("payload")).get("usage"))
        if usage is not None:
            return usage
    return {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}


def _normalize_usage(raw: Any) -> dict[str, int] | None:
    usage = _dict(raw)
    input_tokens = _int_from(usage, "inputTokens", "input_tokens", "prompt_tokens", "promptTokens")
    output_tokens = _int_from(usage, "outputTokens", "output_tokens", "completion_tokens", "completionTokens")
    total_tokens = _int_from(usage, "totalTokens", "total_tokens")
    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens
    if input_tokens == 0 and output_tokens == 0 and total_tokens == 0:
        return None
    return {"inputTokens": input_tokens, "outputTokens": output_tokens, "totalTokens": total_tokens}


def _context_budget(run: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    input_payload = _dict(run.get("input_payload"))
    budget = _dict(input_payload.get("contextBudget"))
    if budget:
        return budget
    for event in reversed(events):
        payload = _dict(event.get("payload"))
        event_budget = _dict(payload.get("contextBudget"))
        if event.get("type") == "context.budget_estimated" and event_budget:
            return event_budget
    return {}


def _prompt_layers(context_budget: dict[str, Any]) -> list[dict[str, Any]]:
    layers = _list(context_budget.get("selectedLayers")) or _list(context_budget.get("layers"))
    return [dict(layer) for layer in layers if isinstance(layer, dict)]


def _compaction_snapshot(run: dict[str, Any], events: list[dict[str, Any]], context_budget: dict[str, Any]) -> dict[str, Any]:
    input_payload = _dict(run.get("input_payload"))
    snapshot = _dict(input_payload.get("compactionSnapshot")) or _dict(context_budget.get("compactionSnapshot"))
    if snapshot:
        return snapshot
    for event in reversed(events):
        if event.get("type") == "context.compaction_completed":
            return _dict(event.get("payload"))
    return {}


def _plan_payload(run: dict[str, Any]) -> dict[str, Any]:
    response_payload = _dict(run.get("response_payload"))
    input_payload = _dict(run.get("input_payload"))
    return _dict(response_payload.get("plan")) or _dict(input_payload.get("plan"))


def _public_args(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if not str(key).startswith("_")}


def _budget_max_tokens(input_payload: dict[str, Any], token_usage: dict[str, int]) -> int:
    raw_budget = _dict(input_payload.get("aiAssistantBudget"))
    max_tokens = _int_from(raw_budget, "maxTokens", "max_tokens")
    if max_tokens:
        return max_tokens
    return max(_int_from(token_usage, "totalTokens"), 1_000_000)


def _budget_max_usd(input_payload: dict[str, Any]) -> float | None:
    raw_budget = _dict(input_payload.get("aiAssistantBudget"))
    value = raw_budget.get("maxUsd") or raw_budget.get("max_usd")
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return max(0.0, float(value))
    if isinstance(value, str):
        try:
            return max(0.0, float(value))
        except ValueError:
            return None
    return None


def _missing_audit_fields(audit: dict[str, Any]) -> list[str]:
    prompt = _dict(audit.get("prompt"))
    checks = {
        "prompt.layers": bool(_list(prompt.get("layers"))),
        "prompt.contextBudget": bool(_dict(prompt.get("contextBudget"))),
        "prompt.compactionSnapshot": bool(_dict(prompt.get("compactionSnapshot"))),
        "plan": bool(_dict(audit.get("plan"))),
        "toolCalls": bool(_list(audit.get("toolCalls"))),
        "retries": bool(_list(audit.get("retries"))),
        "fallbacks": bool(_list(audit.get("fallbacks"))),
        "approvals": bool(_list(audit.get("approvals"))),
        "tokenCost": bool(_dict(audit.get("tokenCost"))),
        "fileDiffs": bool(_list(audit.get("fileDiffs"))),
        "adapterAudits": bool(_list(audit.get("adapterAudits"))),
        "contextBudget": bool(_dict(audit.get("contextBudget"))),
        "compactionSnapshot": bool(_dict(audit.get("compactionSnapshot"))),
        "finalResult": bool(str(audit.get("finalResult") or "")),
    }
    return sorted(field for field in AUDIT_REQUIRED_FIELDS if not checks.get(field))


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _int_from(raw: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            return max(0, int(value))
        if isinstance(value, str) and value.strip().isdigit():
            return int(value)
    return 0


def _int_value(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int | float):
        return max(0, int(value))
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return 0


def _float_from(raw: dict[str, Any], key: str) -> float:
    value = raw.get(key)
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, int | float):
        return max(0.0, float(value))
    if isinstance(value, str):
        try:
            return max(0.0, float(value))
        except ValueError:
            return 0.0
    return 0.0


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return None


def _duration_ms(started: Any, ended: Any) -> int:
    if isinstance(started, datetime) and isinstance(ended, datetime):
        return max(0, int((ended - started).total_seconds() * 1000))
    return 0
