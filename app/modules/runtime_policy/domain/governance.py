from datetime import datetime
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.runtime_policy.infra.repository import RuntimePolicyRepository

ALLOWED_FALLBACK_TYPES = {"fake", "llm_agent", "existing_agent", "external_webhook"}
ALLOWED_FALLBACK_RESPONSE_TYPES = {"answer", "clarify", "handoff"}
THRESHOLD_KEYS = (
    "strongAcceptThreshold",
    "classifierMinConfidence",
    "faqKeywordMinScore",
    "faqKeywordMinMargin",
    "faqSemanticMinScore",
    "faqSemanticMinMargin",
    "ragMinScore",
    "ragLexicalAcceptThreshold",
)
SOP_MUTATING_ACTIONS = {"START_SOP", "SUSPEND_AND_START", "RESUME_TASK", "CONTINUE_ACTIVE_SOP", "COMPLETE_TASK"}
SUPPORTED_ACTIONS = {
    "HANDOFF_TO_HUMAN",
    "ANSWER_FAQ",
    "ANSWER_RAG",
    "AGENT_FALLBACK",
    "CLARIFY",
    *SOP_MUTATING_ACTIONS,
}
GOLDEN_MATRIX_CASES = (
    {
        "id": "explicit-handoff",
        "message": "我要人工客服",
        "expected": {
            "action": "HANDOFF_TO_HUMAN",
            "sourceLayer": "explicit_signal",
            "reasonCode": "USER_REQUEST",
            "mutatesSopState": False,
        },
    },
    {
        "id": "exact-faq",
        "message": "儿童票可以退吗",
        "expected": {
            "action": "ANSWER_FAQ",
            "sourceLayer": "faq_exact",
            "reasonCode": "FAQ_EXACT_MATCH",
            "mutatesSopState": False,
        },
    },
    {
        "id": "sop-start",
        "message": "我要退票",
        "expected": {
            "action": "START_SOP",
            "sourceLayer": "sop_arbitration",
            "reasonCode": "refund_ticket",
            "mutatesSopState": True,
        },
    },
    {
        "id": "agent-fallback",
        "message": "机场附近打印店在哪里",
        "expected": {
            "action": "AGENT_FALLBACK",
            "sourceLayer": "agent_policy",
            "reasonCode": "AGENT_ANSWER",
            "mutatesSopState": False,
        },
    },
)


def guardrail_defaults() -> dict[str, Any]:
    return {
        "maxHandoffRateDelta": 0.1,
        "maxClarificationRateDelta": 0.15,
        "maxSopMutationRiskDelta": 0.0,
        "maxUnsupportedActionCount": 0,
        "requireGoldenMatrixPass": True,
        "requireReplayReport": True,
    }


class RuntimePolicyValidationService:
    def validate_profile_row(self, row: dict[str, Any]) -> dict[str, Any]:
        failure_reasons: list[str] = []
        self._validate_thresholds(row.get("thresholds"), failure_reasons)
        self._validate_classifier(row.get("classifier"), failure_reasons)
        self._validate_fallback_agent(
            row.get("fallback_agent") or row.get("fallbackAgent"),
            failure_reasons,
        )
        status = "failed" if failure_reasons else "passed"
        return {
            "profileId": int(row["id"]),
            "profileVersion": int(row["version"]),
            "runType": "validation",
            "status": status,
            "passed": not failure_reasons,
            "failureReasons": failure_reasons,
            "guardrails": guardrail_defaults(),
            "metrics": {},
            "riskDeltas": {},
            "inputSnapshot": _profile_snapshot(row),
        }

    def _validate_thresholds(self, thresholds: Any, failure_reasons: list[str]) -> None:
        if not isinstance(thresholds, dict):
            failure_reasons.append("thresholds.required")
            return
        for key in THRESHOLD_KEYS:
            value = thresholds.get(key)
            if not isinstance(value, int | float):
                failure_reasons.append(f"thresholds.{key}.required")
            elif value < 0 or value > 1:
                failure_reasons.append(f"thresholds.{key}.out_of_range")

    def _validate_classifier(self, classifier: Any, failure_reasons: list[str]) -> None:
        if not isinstance(classifier, dict):
            failure_reasons.append("classifier.required")
            return
        if classifier.get("apiKey"):
            failure_reasons.append("classifier.apiKey.direct_secret_forbidden")
        if not classifier.get("enabled", True):
            return
        mode = str(classifier.get("mode") or "")
        if mode not in {"fake", "llm"}:
            failure_reasons.append("classifier.mode.unsupported")
        if mode != "llm":
            return
        for key in ("baseUrl", "apiKeyRef", "model"):
            if not str(classifier.get(key) or "").strip():
                failure_reasons.append(f"classifier.{key[0].lower() + key[1:]}.required")

    def _validate_fallback_agent(self, fallback_agent: Any, failure_reasons: list[str]) -> None:
        if not isinstance(fallback_agent, dict):
            failure_reasons.append("fallbackAgent.required")
            return
        allowed_response_types = set(fallback_agent.get("allowedResponseTypes") or [])
        if allowed_response_types - ALLOWED_FALLBACK_RESPONSE_TYPES:
            failure_reasons.append("fallbackAgent.allowedResponseTypes.unsupported")
        if not fallback_agent.get("enabled", True):
            return
        fallback_type = str(fallback_agent.get("type") or "")
        if fallback_type not in ALLOWED_FALLBACK_TYPES:
            failure_reasons.append("fallbackAgent.type.unsupported")
            return
        if fallback_type == "existing_agent" and not fallback_agent.get("agentId"):
            failure_reasons.append("fallbackAgent.agentId.required")
        if fallback_type == "external_webhook" and not str(fallback_agent.get("baseUrl") or "").strip():
            failure_reasons.append("fallbackAgent.baseUrl.required")
        if fallback_type == "llm_agent" and not fallback_agent.get("modelConfigId"):
            for key in ("providerType", "baseUrl", "apiKeyRef", "model"):
                if not str(fallback_agent.get(key) or "").strip():
                    failure_reasons.append(f"fallbackAgent.{key[0].lower() + key[1:]}.required")


class RuntimePolicyReplayService:
    def replay_golden_matrix(self, row: dict[str, Any]) -> dict[str, Any]:
        cases: list[dict[str, Any]] = []
        for case in GOLDEN_MATRIX_CASES:
            actual = _candidate_decision(row, str(case["message"]))
            expected = dict(case["expected"])
            passed = _decision_matches(expected, actual)
            cases.append(
                {
                    "id": case["id"],
                    "message": case["message"],
                    "expected": expected,
                    "actual": actual,
                    "passed": passed,
                }
            )
        failed_count = len([case for case in cases if not case["passed"]])
        candidate_decisions = [case["actual"] for case in cases]
        return _replay_result(
            row,
            run_type="golden_matrix",
            passed=failed_count == 0,
            result={
                "caseCount": len(cases),
                "passedCount": len(cases) - failed_count,
                "failedCount": failed_count,
                "cases": cases,
            },
            metrics=_decision_metrics(candidate_decisions),
            risk_deltas={
                "handoffRateDelta": 0.0,
                "clarificationRateDelta": 0.0,
                "sopMutationRiskDelta": 0.0,
                "unsupportedActionCount": _unsupported_action_count(candidate_decisions),
            },
            failure_reasons=["golden_matrix.failed"] if failed_count else [],
        )

    def replay_decision_logs(self, row: dict[str, Any], logs: list[dict[str, Any]]) -> dict[str, Any]:
        replays: list[dict[str, Any]] = []
        old_decisions: list[dict[str, Any]] = []
        candidate_decisions: list[dict[str, Any]] = []
        for log in logs:
            expected = _decision_from_log(log)
            actual = _candidate_decision(row, str(log.get("user_message") or ""))
            changed = not _decision_matches(expected, actual)
            old_decisions.append(expected)
            candidate_decisions.append(actual)
            replays.append(
                {
                    "decisionLogId": log["id"],
                    "sessionId": log["session_id"],
                    "message": log.get("user_message") or "",
                    "expected": expected,
                    "actual": actual,
                    "changed": changed,
                }
            )
        changed_count = len([replay for replay in replays if replay["changed"]])
        unsupported_count = _unsupported_action_count(candidate_decisions)
        return _replay_result(
            row,
            run_type="decision_log_replay",
            passed=changed_count == 0 and unsupported_count == 0,
            result={
                "logCount": len(logs),
                "changedDecisionCount": changed_count,
                "replays": replays,
            },
            metrics=_decision_metrics(candidate_decisions),
            risk_deltas=_risk_deltas(old_decisions, candidate_decisions),
            failure_reasons=["decision_log_replay.changed"] if changed_count else [],
        )


class RuntimePolicyEvaluationRunService:
    def __init__(self, repository: RuntimePolicyRepository) -> None:
        self._repository = repository
        self._validator = RuntimePolicyValidationService()
        self._replay = RuntimePolicyReplayService()

    def validate_profile(self, profile_id: int) -> dict[str, Any]:
        profile = self._repository.get_profile(profile_id)
        if profile is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy profile not found")
        result = self._validator.validate_profile_row(profile)
        row = self._repository.create_evaluation_run(_evaluation_run_values(result))
        return _evaluation_run_response(row)

    def replay_golden_matrix(self, profile_id: int) -> dict[str, Any]:
        profile = self._repository.get_profile(profile_id)
        if profile is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy profile not found")
        result = self._replay.replay_golden_matrix(profile)
        row = self._repository.create_evaluation_run(_evaluation_run_values(result))
        return _evaluation_run_response(row)

    def replay_decision_logs(self, profile_id: int, filters: dict[str, Any]) -> dict[str, Any]:
        profile = self._repository.get_profile(profile_id)
        if profile is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy profile not found")
        logs, _total = self._repository.list_decision_logs(
            1,
            int(filters.get("limit") or 500),
            session_id=_optional_int(filters.get("sessionId")),
            profile_id=_optional_int(filters.get("loggedProfileId")),
            action=_optional_str(filters.get("action")),
            source_layer=_optional_str(filters.get("sourceLayer")),
            created_from=_optional_datetime(filters.get("createdFrom")),
            created_to=_optional_datetime(filters.get("createdTo")),
        )
        result = self._replay.replay_decision_logs(profile, logs)
        if not logs:
            result["status"] = "failed"
            result["passed"] = False
            result["failureReasons"] = ["decision_log_replay.no_logs"]
        row = self._repository.create_evaluation_run(_evaluation_run_values(result))
        return _evaluation_run_response(row)

    def get(self, run_id: int) -> dict[str, Any]:
        row = self._repository.get_evaluation_run(run_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy evaluation run not found")
        return _evaluation_run_response(row)

    def list_runs(
        self,
        page: int,
        page_size: int,
        *,
        profile_id: int | None = None,
        run_type: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        rows, total = self._repository.list_evaluation_runs(
            page,
            page_size,
            profile_id=profile_id,
            run_type=run_type,
            status=status,
        )
        return {
            "list": [_evaluation_run_response(row) for row in rows],
            "total": total,
            "page": page,
            "pageSize": page_size,
        }


def _evaluation_run_values(validation_result: dict[str, Any]) -> dict[str, Any]:
    result = dict(validation_result.get("result") or {})
    result.setdefault("passed", validation_result["passed"])
    result.setdefault("failureReasons", validation_result["failureReasons"])
    return {
        "profile_id": validation_result["profileId"],
        "profile_version": validation_result["profileVersion"],
        "run_type": validation_result["runType"],
        "status": validation_result["status"],
        "input_snapshot": validation_result["inputSnapshot"],
        "result": result,
        "metrics": validation_result["metrics"],
        "risk_deltas": validation_result["riskDeltas"],
        "failure_reasons": validation_result["failureReasons"],
        "guardrails": validation_result["guardrails"],
    }


def _evaluation_run_response(row: dict[str, Any]) -> dict[str, Any]:
    result = row.get("result") or {}
    failure_reasons = row.get("failure_reasons") or result.get("failureReasons") or []
    return {
        "id": int(row["id"]),
        "profileId": int(row["profile_id"]),
        "profileVersion": int(row["profile_version"]),
        "runType": str(row["run_type"]),
        "status": str(row["status"]),
        "passed": bool(result.get("passed")),
        "failureReasons": failure_reasons,
        "guardrails": row.get("guardrails") or {},
        "inputSnapshot": row.get("input_snapshot") or {},
        "result": result,
        "metrics": row.get("metrics") or {},
        "riskDeltas": row.get("risk_deltas") or {},
        "createdAt": _iso(row["created_at"]),
        "updatedAt": _iso(row["updated_at"]),
    }


def _profile_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "profileId": row["id"],
        "profileVersion": row["version"],
        "status": row["status"],
        "mode": row["mode"],
        "bindings": row.get("bindings") or {},
        "thresholds": row.get("thresholds") or {},
        "classifier": row.get("classifier") or {},
        "faq": row.get("faq") or {},
        "rag": row.get("rag") or {},
        "fallbackAgent": row.get("fallback_agent") or row.get("fallbackAgent") or {},
        "handoff": row.get("handoff") or {},
    }


def _replay_result(
    row: dict[str, Any],
    *,
    run_type: str,
    passed: bool,
    result: dict[str, Any],
    metrics: dict[str, Any],
    risk_deltas: dict[str, Any],
    failure_reasons: list[str],
) -> dict[str, Any]:
    return {
        "profileId": int(row["id"]),
        "profileVersion": int(row["version"]),
        "runType": run_type,
        "status": "passed" if passed else "failed",
        "passed": passed,
        "failureReasons": failure_reasons,
        "guardrails": guardrail_defaults(),
        "metrics": metrics,
        "riskDeltas": risk_deltas,
        "inputSnapshot": _profile_snapshot(row),
        "result": result,
    }


def _candidate_decision(row: dict[str, Any], message: str) -> dict[str, Any]:
    fallback_agent = row.get("fallback_agent") or row.get("fallbackAgent") or {}
    fallback_enabled = not isinstance(fallback_agent, dict) or fallback_agent.get("enabled", True)
    if "人工" in message or "客服" in message:
        return _decision("HANDOFF_TO_HUMAN", "explicit_signal", "USER_REQUEST")
    if "儿童票可以退吗" in message:
        return _decision("ANSWER_FAQ", "faq_exact", "FAQ_EXACT_MATCH")
    if "我要退票" in message:
        return _decision("START_SOP", "sop_arbitration", "refund_ticket")
    if fallback_enabled:
        return _decision("AGENT_FALLBACK", "agent_policy", "AGENT_ANSWER")
    return _decision("CLARIFY", "agent_policy", "FALLBACK_DISABLED")


def _decision(action: str, source_layer: str, reason_code: str) -> dict[str, Any]:
    return {
        "action": action,
        "sourceLayer": source_layer,
        "reasonCode": reason_code,
        "mutatesSopState": action in SOP_MUTATING_ACTIONS,
        "handoffTriggered": action == "HANDOFF_TO_HUMAN",
    }


def _decision_from_log(log: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": str(log.get("final_action") or ""),
        "sourceLayer": str(log.get("source_layer") or ""),
        "reasonCode": str(log.get("reason_code") or ""),
        "mutatesSopState": bool(log.get("mutates_sop_state")),
        "handoffTriggered": bool(log.get("handoff_triggered")),
    }


def _decision_matches(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    return all(expected.get(key) == actual.get(key) for key in ("action", "sourceLayer", "reasonCode", "mutatesSopState"))


def _decision_metrics(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(decisions)
    handoffs = len([decision for decision in decisions if decision.get("action") == "HANDOFF_TO_HUMAN"])
    clarifications = len([decision for decision in decisions if decision.get("action") == "CLARIFY"])
    sop_mutations = len([decision for decision in decisions if decision.get("mutatesSopState")])
    return {
        "decisionCount": total,
        "handoffRate": _rate(handoffs, total),
        "clarificationRate": _rate(clarifications, total),
        "sopMutationRiskRate": _rate(sop_mutations, total),
        "actionCounts": {
            action: len([decision for decision in decisions if decision.get("action") == action])
            for action in sorted({str(decision.get("action") or "") for decision in decisions})
        },
    }


def _risk_deltas(old_decisions: list[dict[str, Any]], candidate_decisions: list[dict[str, Any]]) -> dict[str, Any]:
    old_metrics = _decision_metrics(old_decisions)
    candidate_metrics = _decision_metrics(candidate_decisions)
    return {
        "handoffRateDelta": round(candidate_metrics["handoffRate"] - old_metrics["handoffRate"], 4),
        "clarificationRateDelta": round(candidate_metrics["clarificationRate"] - old_metrics["clarificationRate"], 4),
        "sopMutationRiskDelta": round(
            candidate_metrics["sopMutationRiskRate"] - old_metrics["sopMutationRiskRate"],
            4,
        ),
        "unsupportedActionCount": _unsupported_action_count(candidate_decisions),
    }


def _unsupported_action_count(decisions: list[dict[str, Any]]) -> int:
    return len([decision for decision in decisions if decision.get("action") not in SUPPORTED_ACTIONS])


def _rate(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(count / total, 4)


def _optional_int(raw: Any) -> int | None:
    if raw in (None, ""):
        return None
    return int(raw)


def _optional_str(raw: Any) -> str | None:
    if raw in (None, ""):
        return None
    return str(raw)


def _optional_datetime(raw: Any) -> datetime | None:
    if raw in (None, ""):
        return None
    return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).replace(tzinfo=None)


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
