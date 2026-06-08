from datetime import datetime
from typing import Any

from app.modules.runtime_lab.domain.router import RouteDecision


def format_turn(turn: Any) -> dict[str, Any]:
    return {
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
    return {
        "id": row["id"],
        "sessionId": row["session_id"],
        "sopId": row["sop_id"],
        "status": row["status"],
        "currentStep": row["current_step"],
        "checkpointId": row["checkpoint_id"],
        "parentTaskId": row["parent_task_id"],
        "resumeSummary": row["resume_summary"],
        "businessRefs": row["business_refs"] or {},
        "suspendedAt": _format_datetime(row.get("suspended_at")),
        "completedAt": _format_datetime(row.get("completed_at")),
        "createdAt": _format_datetime(row.get("created_at")),
        "updatedAt": _format_datetime(row.get("updated_at")),
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
