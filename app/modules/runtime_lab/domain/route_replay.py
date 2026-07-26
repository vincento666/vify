from collections.abc import Mapping
from typing import Any

from app.modules.runtime_lab.domain.payload import format_route_decision
from app.modules.runtime_lab.domain.service import RuntimeLabService

SOP_MUTATING_ACTIONS = {
    "START_SOP",
    "SUSPEND_AND_START",
    "RESUME_TASK",
    "CONTINUE_ACTIVE_SOP",
    "COMPLETE_TASK",
}


def replay_runtime_route(
    service: RuntimeLabService,
    case: dict[str, Any],
) -> dict[str, Any]:
    context = _mapping(case.get("initialRouteContext"))
    enabled_ids = case.get("enabledIntentIds")
    enabled_sop_ids = (
        [str(intent_id) for intent_id in enabled_ids]
        if isinstance(enabled_ids, list | tuple)
        else None
    )
    decision = service.preview_route(
        _last_message(case.get("turns")),
        session_id=_non_negative_int(context.get("sessionId")),
        active_task=_optional_mapping(context.get("activeTask")),
        suspended_tasks=_mapping_list(context.get("suspendedTasks")),
        enabled_sop_ids=enabled_sop_ids,
    )
    payload = format_route_decision(decision)
    return {
        "action": decision.action,
        "sourceLayer": _source_layer(payload),
        "reasonCode": _reason_code(payload),
        "targetSopId": decision.target_sop_id,
        "clarificationQuestion": _clarification_question(payload),
        "mutatesSopState": decision.action in SOP_MUTATING_ACTIONS,
        "handoffTriggered": decision.action == "HANDOFF_TO_HUMAN",
        "recalledCandidateIds": _candidate_ids(payload),
        "providerUsage": _provider_usage(payload),
        "elapsedMs": 0,
    }


def _last_message(turns: object) -> str:
    if not isinstance(turns, list | tuple) or not turns:
        return ""
    turn = turns[-1]
    if not isinstance(turn, Mapping):
        return ""
    return str(turn.get("message") or turn.get("content") or "")


def _source_layer(route_decision: dict[str, Any]) -> str:
    for key in ("handoff", "agentAnswer", "faqAnswer", "ragAnswer"):
        value = route_decision.get(key)
        if isinstance(value, Mapping) and value.get("sourceLayer"):
            return str(value["sourceLayer"])
    action = str(route_decision.get("action") or "")
    if action == "AGENT_FALLBACK":
        return "agent_policy"
    policy_gate = route_decision.get("policyGate")
    if isinstance(policy_gate, Mapping) and policy_gate.get("stage"):
        return str(policy_gate["stage"])
    final_decision = route_decision.get("finalDecision")
    if isinstance(final_decision, Mapping) and final_decision.get("sourceLayer"):
        return str(final_decision["sourceLayer"])
    return ""


def _reason_code(route_decision: dict[str, Any]) -> str:
    for key in ("handoff", "agentAnswer", "faqAnswer", "ragAnswer"):
        value = route_decision.get(key)
        if isinstance(value, Mapping) and value.get("reasonCode"):
            return str(value["reasonCode"])
    action = str(route_decision.get("action") or "")
    if action == "AGENT_FALLBACK":
        return "AGENT_ANSWER"
    if action in SOP_MUTATING_ACTIONS:
        return action
    classifier = route_decision.get("classifierResult")
    if isinstance(classifier, Mapping) and action == "CLARIFY":
        return "LOW_CONFIDENCE"
    final_decision = route_decision.get("finalDecision")
    if isinstance(final_decision, Mapping) and final_decision.get("reasonCode"):
        return str(final_decision["reasonCode"])
    return str(route_decision.get("reason") or "")


def _clarification_question(route_decision: dict[str, Any]) -> str | None:
    projected = route_decision.get("clarificationQuestion")
    if projected:
        return str(projected)
    classifier = route_decision.get("classifierResult")
    if not isinstance(classifier, Mapping):
        return None
    value = classifier.get("clarification_question")
    return str(value) if value else None


def _candidate_ids(route_decision: dict[str, Any]) -> list[str]:
    candidates = route_decision.get("candidates")
    if not isinstance(candidates, list):
        return []
    return [
        str(candidate.get("candidate_id") or candidate.get("candidateId"))
        for candidate in candidates
        if isinstance(candidate, Mapping)
        and (candidate.get("candidate_id") or candidate.get("candidateId"))
    ]


def _provider_usage(route_decision: dict[str, Any]) -> dict[str, int]:
    classifier = route_decision.get("classifierResult")
    used_real_llm = bool(
        isinstance(classifier, Mapping)
        and classifier.get("used_real_llm")
    )
    calls = int(used_real_llm)
    return {"totalCalls": calls, "liveCalls": calls, "paidCalls": calls}


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _optional_mapping(value: object) -> dict[str, Any] | None:
    return dict(value) if isinstance(value, Mapping) else None


def _mapping_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list | tuple):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        parsed = int(value)
    elif isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return 0
    else:
        return 0
    return max(0, parsed)
