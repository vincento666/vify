from __future__ import annotations

from typing import Any


def build_composer_run_debug(
    detail: dict[str, Any],
    *,
    owner_type: str,
    owner_id: int,
) -> dict[str, Any]:
    node_details = [_node_detail(node) for node in detail.get("nodeRuns", [])]
    return {
        "runId": int(detail["runId"]),
        "ownerType": owner_type,
        "ownerId": owner_id,
        "status": detail.get("status", ""),
        "elapsedMs": int(detail.get("elapsedMs") or 0),
        "createdAt": detail.get("createdAt"),
        "finishedAt": detail.get("finishedAt"),
        "input": detail.get("input") or {},
        "output": detail.get("output") or {},
        "error": detail.get("error") or "",
        "callTree": _call_tree(node_details),
        "flamegraph": _flamegraph(node_details),
        "nodeDetails": node_details,
        "events": detail.get("events") or [],
        "streamEvents": _stream_events(node_details),
    }


def _call_tree(node_details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "nodeKey": node["nodeKey"],
            "nodeType": node["nodeType"],
            "status": node["status"],
            "elapsedMs": node["elapsedMs"],
            "parentNodeKey": node_details[index - 1]["nodeKey"] if index > 0 else "",
        }
        for index, node in enumerate(node_details)
    ]


def _flamegraph(node_details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = 0
    for node in node_details:
        duration = max(0, int(node.get("elapsedMs") or 0))
        rows.append(
            {
                "nodeKey": node["nodeKey"],
                "label": f"{node['nodeType']} {node['nodeKey']}".strip(),
                "startMs": cursor,
                "durationMs": duration,
                "status": node["status"],
            }
        )
        cursor += duration
    return rows


def _node_detail(node: dict[str, Any]) -> dict[str, Any]:
    outputs = node.get("outputs") if isinstance(node.get("outputs"), dict) else {}
    node_type = str(node.get("nodeType") or "")
    elapsed_ms = int(node.get("elapsedMs") or 0)
    events = _node_events(node_type, str(node.get("nodeKey") or ""), outputs)
    input_summary = _summary(node.get("inputs") or node.get("input") or {})
    output_summary = _summary(_summary_outputs(outputs))
    usage = _usage_projection(events, input_summary, output_summary)
    evidence = outputs.get("evidence") if isinstance(outputs.get("evidence"), dict) else {}
    error = str(node.get("error") or "")

    return {
        "id": node.get("id"),
        "nodeKey": node.get("nodeKey", ""),
        "nodeType": node_type,
        "status": node.get("status", ""),
        "elapsedMs": elapsed_ms,
        "latencyMs": elapsed_ms,
        "outputs": outputs,
        "error": error,
        "inputSummary": input_summary,
        "outputSummary": output_summary,
        "errorSummary": error,
        "resourceType": str(evidence.get("resourceType") or outputs.get("resourceType") or node_type),
        "resourceId": evidence.get("resourceId") or outputs.get("resourceId") or "",
        "events": events,
        **usage,
    }


def _usage_projection(events: list[dict[str, Any]], input_summary: str, output_summary: str) -> dict[str, Any]:
    usage_event = next((event for event in events if event.get("type") == "node_usage"), None)
    input_tokens = _optional_int((usage_event or {}).get("inputTokens"))
    output_tokens = _optional_int((usage_event or {}).get("outputTokens"))
    total_tokens = _optional_int((usage_event or {}).get("totalTokens"))
    cost_estimate = (usage_event or {}).get("costEstimate")

    usage_estimated = not usage_event
    if input_tokens is None:
        input_tokens = _estimate_tokens(input_summary)
        usage_estimated = True
    if output_tokens is None:
        output_tokens = _estimate_tokens(output_summary)
        usage_estimated = True
    if total_tokens is None:
        total_tokens = input_tokens + output_tokens
        usage_estimated = True

    return {
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": total_tokens,
        "costEstimate": cost_estimate,
        "usageEstimated": usage_estimated,
    }


def _node_events(node_type: str, node_key: str, outputs: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    raw_events = outputs.get("events")
    if isinstance(raw_events, list):
        for raw_event in raw_events:
            event = _stream_event(raw_event, node_key)
            if event is not None:
                events.append(event)
    if node_type.upper() == "END":
        content = _stream_content(outputs)
        if content and not any(event.get("type") == "message_done" for event in events):
            events.append({"type": "message_delta", "nodeKey": node_key, "content": content})
            events.append({"type": "message_done", "nodeKey": node_key, "content": content})
    return events


def _summary_outputs(outputs: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in outputs.items() if key not in {"events", "evidence", "toolCalls"}}


def _summary(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        text = str(value)
    text = " ".join(text.split())
    return text[:500]


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _estimate_tokens(text: str) -> int:
    text = text.strip()
    if not text:
        return 0
    return max(1, len(text.split()))


def _stream_events(node_details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for node in node_details:
        node_key = str(node.get("nodeKey") or "")
        outputs = node.get("outputs") if isinstance(node.get("outputs"), dict) else {}
        raw_events = outputs.get("events") if isinstance(outputs, dict) else []
        if isinstance(raw_events, list):
            for raw_event in raw_events:
                event = _stream_event(raw_event, node_key)
                if event is not None:
                    events.append(event)
        if str(node.get("nodeType") or "").upper() == "END":
            content = _stream_content(outputs)
            if content:
                events.append({"type": "message_delta", "nodeKey": node_key, "content": content})
                events.append({"type": "message_done", "nodeKey": node_key, "content": content})
    return events


def _stream_event(raw_event: Any, fallback_node_key: str) -> dict[str, Any] | None:
    if not isinstance(raw_event, dict):
        return None
    event_type = str(raw_event.get("type") or "")
    if event_type not in {"message_delta", "message_done", "llm_delta", "stream_error", "node_usage"}:
        return None
    event = {
        "type": event_type,
        "nodeKey": str(raw_event.get("nodeKey") or fallback_node_key),
        "content": str(raw_event.get("content") or ""),
    }
    if event_type == "stream_error":
        event["error"] = str(raw_event.get("error") or raw_event.get("message") or "")
    if event_type == "node_usage":
        for key in ("inputTokens", "outputTokens", "totalTokens", "costEstimate"):
            if key in raw_event:
                event[key] = raw_event.get(key)
    return event


def _stream_content(outputs: dict[str, Any]) -> str:
    for key in ("output", "answer", "final", "content"):
        value = outputs.get(key)
        if _streamable(value):
            return str(value)
    for key, value in outputs.items():
        if key in {"events", "toolCalls", "interrupt"}:
            continue
        if _streamable(value):
            return str(value)
    return ""


def _streamable(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) and str(value) != ""
