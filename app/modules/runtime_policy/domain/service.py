from datetime import datetime
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.runtime_policy.infra.repository import RuntimePolicyRepository
from app.modules.runtime_policy.web.schemas import RuntimePolicyProfileRequest, RuntimePolicyProfileResponse


class RuntimePolicyProfileService:
    def __init__(self, repository: RuntimePolicyRepository) -> None:
        self._repository = repository

    def create_profile(self, request: RuntimePolicyProfileRequest) -> dict[str, Any]:
        row = self._repository.create_profile(_profile_values(request))
        return _profile_response(row)

    def list_profiles(
        self,
        page: int,
        page_size: int,
        *,
        status: str | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]:
        rows, total = self._repository.list_profiles(page, page_size, status=status, mode=mode)
        return {
            "list": [_profile_response(row) for row in rows],
            "total": total,
            "page": page,
            "pageSize": page_size,
        }

    def get_profile(self, profile_id: int) -> dict[str, Any]:
        row = self._repository.get_profile(profile_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy profile not found")
        return _profile_response(row)

    def update_profile(self, profile_id: int, request: RuntimePolicyProfileRequest) -> dict[str, Any]:
        row = self._repository.update_profile(profile_id, _profile_values(request))
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy profile not found")
        return _profile_response(row)

    def delete_profile(self, profile_id: int) -> None:
        if not self._repository.delete_profile(profile_id):
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy profile not found")

    def preview_profile(self, profile_id: int, request: RuntimePolicyProfileRequest | None = None) -> dict[str, Any]:
        profile = self.get_profile(profile_id)
        if request is not None:
            profile = {
                **profile,
                **RuntimePolicyProfileResponse(
                    id=profile_id,
                    version=int(profile["version"]),
                    createdAt=profile["createdAt"],
                    updatedAt=profile["updatedAt"],
                    **_profile_values(request),
                ).model_dump(by_alias=True),
            }
        return {
            "profileId": profile_id,
            "profileVersion": profile["version"],
            "policySnapshot": _policy_snapshot(profile),
        }


class RuntimeDecisionLogService:
    def __init__(self, repository: RuntimePolicyRepository) -> None:
        self._repository = repository

    def record_message_decision(
        self,
        *,
        session_id: int,
        message_id: str,
        user_message: str,
        command_payload: dict[str, Any],
        effective_policy: dict[str, Any],
        route_context_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        route_decision = dict(command_payload.get("routeDecision") or {})
        values = _decision_log_values(
            session_id=session_id,
            message_id=message_id,
            user_message=user_message,
            command_payload=command_payload,
            effective_policy=effective_policy,
            route_decision=route_decision,
            route_context_snapshot=route_context_snapshot,
        )
        return _decision_log_response(self._repository.create_decision_log(values))

    def get(self, log_id: int) -> dict[str, Any]:
        row = self._repository.get_decision_log(log_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime decision log not found")
        return _decision_log_response(row)

    def list_logs(
        self,
        page: int,
        page_size: int,
        *,
        session_id: int | None = None,
        profile_id: int | None = None,
        action: str | None = None,
        source_layer: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> dict[str, Any]:
        rows, total = self._repository.list_decision_logs(
            page,
            page_size,
            session_id=session_id,
            profile_id=profile_id,
            action=action,
            source_layer=source_layer,
            created_from=created_from,
            created_to=created_to,
        )
        return {
            "list": [_decision_log_response(row) for row in rows],
            "total": total,
            "page": page,
            "pageSize": page_size,
        }


def _profile_values(request: RuntimePolicyProfileRequest) -> dict[str, Any]:
    return {
        "name": request.name,
        "description": request.description,
        "status": request.status,
        "mode": request.mode,
        "bindings": request.bindings.model_dump(mode="json", by_alias=True),
        "thresholds": request.thresholds.model_dump(mode="json", by_alias=True),
        "classifier": request.classifier.model_dump(mode="json", by_alias=True),
        "faq": request.faq.model_dump(mode="json", by_alias=True),
        "rag": request.rag.model_dump(mode="json", by_alias=True),
        "fallback_agent": request.fallback_agent.model_dump(mode="json", by_alias=True),
        "handoff": request.handoff.model_dump(mode="json", by_alias=True),
        "audit": request.audit.model_dump(mode="json", by_alias=True),
    }


def _profile_response(row: dict[str, Any]) -> dict[str, Any]:
    response = RuntimePolicyProfileResponse(
        id=int(row["id"]),
        version=int(row["version"]),
        name=str(row["name"]),
        description=str(row.get("description") or ""),
        status=str(row["status"]),
        mode=str(row["mode"]),
        bindings=row["bindings"],
        thresholds=row["thresholds"],
        classifier=row["classifier"],
        faq=row["faq"],
        rag=row["rag"],
        fallbackAgent=row["fallback_agent"],
        handoff=row["handoff"],
        audit=row["audit"],
        createdAt=row["created_at"].isoformat(),
        updatedAt=row["updated_at"].isoformat(),
    )
    return response.model_dump(by_alias=True)


def _policy_snapshot(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "profileId": profile["id"],
        "profileVersion": profile["version"],
        "status": profile["status"],
        "mode": profile["mode"],
        "bindings": profile["bindings"],
        "thresholds": profile["thresholds"],
        "classifier": profile["classifier"],
        "faq": profile["faq"],
        "rag": profile["rag"],
        "fallbackAgent": profile["fallbackAgent"],
        "handoff": profile["handoff"],
    }


def _decision_log_values(
    *,
    session_id: int,
    message_id: str,
    user_message: str,
    command_payload: dict[str, Any],
    effective_policy: dict[str, Any],
    route_decision: dict[str, Any],
    route_context_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    source_layer = _decision_source_layer(route_decision)
    reason_code = _decision_reason_code(route_decision)
    route_context = route_context_snapshot or {
        "snapshotVersion": "legacy-command-result/v0",
        "activeTask": command_payload.get("activeTask"),
        "suspendedTasks": command_payload.get("suspendedTasks") or [],
    }
    return {
        "session_id": session_id,
        "message_id": message_id,
        "user_message": user_message,
        "active_task_snapshot": route_context.get("activeTask"),
        "suspended_task_snapshot": route_context.get("suspendedTasks") or [],
        "policy_profile_id": effective_policy.get("profileId"),
        "policy_profile_version": effective_policy.get("profileVersion"),
        "policy_snapshot": effective_policy.get("policySnapshot") or {},
        "candidate_scores": _candidate_scores(route_decision),
        "faq_score": _nested_float(route_decision, "faqAnswer", "score"),
        "faq_margin": _nested_float(route_decision, "faqAnswer", "margin"),
        "semantic_score": _nested_float(route_decision, "faqAnswer", "semanticScore"),
        "semantic_margin": _nested_float(route_decision, "faqAnswer", "semanticMargin"),
        "rag_score": _nested_float(route_decision, "ragAnswer", "score"),
        "rag_lexical_overlap": _nested_float(route_decision, "ragAnswer", "lexicalOverlap"),
        "classifier_confidence": _nested_float(route_decision, "classifierResult", "confidence"),
        "agent_confidence": _nested_float(route_decision, "agentAnswer", "confidence"),
        "final_action": str(route_decision.get("action") or ""),
        "source_layer": source_layer,
        "reason_code": reason_code,
        "mutates_sop_state": str(route_decision.get("action") or "") in {"START_SOP", "SUSPEND_AND_START", "RESUME_TASK", "CONTINUE_ACTIVE_SOP", "COMPLETE_TASK"},
        "handoff_triggered": str(route_decision.get("action") or "") == "HANDOFF_TO_HUMAN",
        "route_evidence": {
            "routeDecision": route_decision,
            "routeContextSnapshot": route_context,
            "reply": command_payload.get("reply"),
            "resumeOffer": command_payload.get("resumeOffer"),
        },
    }


def _decision_log_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "sessionId": int(row["session_id"]),
        "messageId": str(row.get("message_id") or ""),
        "userMessage": str(row.get("user_message") or ""),
        "activeTaskSnapshot": row.get("active_task_snapshot"),
        "suspendedTaskSnapshot": row.get("suspended_task_snapshot"),
        "policyProfileId": row.get("policy_profile_id"),
        "policyProfileVersion": row.get("policy_profile_version"),
        "policySnapshot": row.get("policy_snapshot") or {},
        "candidateScores": row.get("candidate_scores") or [],
        "faqScore": row.get("faq_score"),
        "faqMargin": row.get("faq_margin"),
        "semanticScore": row.get("semantic_score"),
        "semanticMargin": row.get("semantic_margin"),
        "ragScore": row.get("rag_score"),
        "ragLexicalOverlap": row.get("rag_lexical_overlap"),
        "classifierConfidence": row.get("classifier_confidence"),
        "agentConfidence": row.get("agent_confidence"),
        "finalAction": str(row.get("final_action") or ""),
        "sourceLayer": str(row.get("source_layer") or ""),
        "reasonCode": str(row.get("reason_code") or ""),
        "mutatesSopState": bool(row.get("mutates_sop_state")),
        "handoffTriggered": bool(row.get("handoff_triggered")),
        "routeEvidence": row.get("route_evidence") or {},
        "createdAt": row["created_at"].isoformat(),
    }


def _decision_source_layer(route_decision: dict[str, Any]) -> str:
    for key in ("handoff", "agentAnswer", "faqAnswer", "ragAnswer"):
        value = route_decision.get(key)
        if isinstance(value, dict) and value.get("sourceLayer"):
            return str(value["sourceLayer"])
    policy_gate = route_decision.get("policyGate")
    if isinstance(policy_gate, dict) and policy_gate.get("stage"):
        return str(policy_gate["stage"])
    final_decision = route_decision.get("finalDecision")
    if isinstance(final_decision, dict) and final_decision.get("sourceLayer"):
        return str(final_decision["sourceLayer"])
    return ""


def _decision_reason_code(route_decision: dict[str, Any]) -> str:
    for key in ("handoff", "agentAnswer", "faqAnswer", "ragAnswer"):
        value = route_decision.get(key)
        if isinstance(value, dict) and value.get("reasonCode"):
            return str(value["reasonCode"])
    final_decision = route_decision.get("finalDecision")
    if isinstance(final_decision, dict) and final_decision.get("reasonCode"):
        return str(final_decision["reasonCode"])
    return str(route_decision.get("reason") or "")


def _candidate_scores(route_decision: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = route_decision.get("candidates")
    if not isinstance(candidates, list):
        return []
    scores: list[dict[str, Any]] = []
    for candidate in candidates:
        if isinstance(candidate, dict):
            scores.append(
                {
                    "candidateId": candidate.get("candidateId") or candidate.get("candidate_id"),
                    "candidateType": candidate.get("candidateType") or candidate.get("candidate_type"),
                    "targetId": candidate.get("targetId") or candidate.get("target_id"),
                    "score": candidate.get("score"),
                    "source": candidate.get("source"),
                }
            )
    return scores


def _nested_float(payload: dict[str, Any], key: str, nested_key: str) -> float | None:
    value = payload.get(key)
    if not isinstance(value, dict):
        return None
    raw = value.get(nested_key)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None
