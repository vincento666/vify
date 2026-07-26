from datetime import datetime
from typing import Any

from app.modules.runtime_lab.domain.router import RouteDecision


def format_turn(turn: Any) -> dict[str, Any]:
    gateway = turn.gateway or {}
    return {
        "sessionId": gateway.get("sessionId"),
        "conversationId": gateway.get("conversationId"),
        "currentSopId": gateway.get("currentSopId"),
        "runId": gateway.get("runId"),
        "intent": gateway.get("intent"),
        "status": gateway.get("status"),
        "answer": gateway.get("answer"),
        "latencyMs": gateway.get("latencyMs", 0),
        "reply": turn.reply,
        "routeDecision": format_route_decision(turn.route_decision),
        "activeTask": format_task(turn.active_task) if turn.active_task else None,
        "suspendedTasks": [format_task(task) for task in turn.suspended_tasks],
        "resumeOffer": turn.resume_offer,
        "events": [format_event(event) for event in turn.events],
    }


def format_session(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "status": row["status"],
        "activeTaskId": row["active_task_id"],
        "version": row["version"],
        "createdAt": _format_datetime(row.get("created_at")),
        "updatedAt": _format_datetime(row.get("updated_at")),
    }


def format_task(row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": row["id"],
        "sessionId": row["session_id"],
        "sopId": row["sop_id"],
        "status": row["status"],
        "parentTaskId": row["parent_task_id"],
        "resumeSummary": row["resume_summary"],
        "suspendedAt": _format_datetime(row.get("suspended_at")),
        "completedAt": _format_datetime(row.get("completed_at")),
        "createdAt": _format_datetime(row.get("created_at")),
        "updatedAt": _format_datetime(row.get("updated_at")),
    }
    chatflow_session = chatflow_session_projection(row)
    if chatflow_session is not None:
        result["chatflowSession"] = chatflow_session
    return result


def chatflow_session_projection(row: dict[str, Any]) -> dict[str, Any] | None:
    """Build the chatflowSession block from runtime ref columns on a task row.

    Returns ``None`` when the task lacks chatflow refs (e.g. SOP without a
    chatflow binding), so callers can omit the field rather than emit empty
    placeholders.
    """
    chatflow_id = row.get("chatflow_id")
    run_id = row.get("chatflow_run_id")
    if not chatflow_id or not run_id:
        return None
    chatflow_id_int = int(chatflow_id)
    run_id_int = int(run_id)
    session_id_raw = row.get("chatflow_session_id")
    event_id_raw = row.get("chatflow_event_id")
    checkpoint_id_raw = row.get("chatflow_checkpoint_id")
    runtime_version = row.get("runtime_version") or "v2"
    return {
        "chatflowId": chatflow_id_int,
        "sessionId": int(session_id_raw) if session_id_raw is not None else None,
        "runId": run_id_int,
        "eventId": int(event_id_raw) if event_id_raw is not None else None,
        "checkpointId": int(checkpoint_id_raw) if checkpoint_id_raw is not None else None,
        "runtimeVersion": str(runtime_version),
        "statusRef": f"/api/v1/runtime-runs/{run_id_int}",
        "eventsRef": f"/api/v1/runtime-runs/{run_id_int}/events",
        "eventStreamRef": f"/api/v1/runtime-runs/{run_id_int}/events/stream?afterSequence=0",
        "nodesRef": f"/api/v1/runtime-runs/{run_id_int}/nodes",
        "resultRef": f"/api/v1/runtime-runs/{run_id_int}/result",
    }


def format_event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "sessionId": row["session_id"],
        "sequence": row["sequence"],
        "eventType": row["event_type"],
        "payload": row["payload"] or {},
        "createdAt": _format_datetime(row.get("created_at")),
    }


def format_route_decision(decision: RouteDecision) -> dict[str, Any]:
    return {
        "action": decision.action,
        "reason": decision.reason,
        "targetSopId": decision.target_sop_id,
        "activeTaskId": decision.active_task_id,
        "matchedKeyword": decision.matched_keyword,
        "clarificationQuestion": decision.clarification_question,
        "candidates": decision.candidates or [],
        "candidateSources": decision.candidate_sources or [],
        "policyGate": decision.policy_gate,
        "classifierRequest": decision.classifier_request,
        "classifierResult": decision.classifier_result,
        "handoff": decision.handoff,
        "faqAnswer": decision.faq_answer,
        "ragAnswer": decision.rag_answer,
        "agentAnswer": decision.agent_answer,
        "finalDecision": decision.final_decision or _final_decision(decision),
    }


def _format_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _final_decision(decision: RouteDecision) -> dict[str, Any]:
    payload = {
        "action": decision.action,
        "targetSopId": decision.target_sop_id,
        "activeTaskId": decision.active_task_id,
    }
    if decision.action in _SOP_ARBITRATION_ACTIONS:
        payload["sourceLayer"] = "sop_arbitration"
        payload["reasonCode"] = decision.action
    if decision.handoff:
        payload["sourceLayer"] = decision.handoff.get("sourceLayer")
        payload["reasonCode"] = decision.handoff.get("reasonCode")
    if decision.faq_answer:
        payload["sourceLayer"] = decision.faq_answer.get("sourceLayer")
        payload["reasonCode"] = decision.faq_answer.get("reasonCode")
    if decision.rag_answer:
        payload["sourceLayer"] = decision.rag_answer.get("sourceLayer")
        payload["reasonCode"] = decision.rag_answer.get("reasonCode")
    if decision.agent_answer:
        payload["sourceLayer"] = decision.agent_answer.get("sourceLayer")
        payload["reasonCode"] = decision.agent_answer.get("reasonCode")
    return payload


_SOP_ARBITRATION_ACTIONS = {
    "CONTINUE_ACTIVE_SOP",
    "START_SOP",
    "SUSPEND_AND_START",
    "RESUME_TASK",
    "REJECT_SWITCH_CONTINUE_ACTIVE",
    "REJECT_SWITCH_SUSPENDED_LIMIT",
    "COMPLETE_TASK",
}
