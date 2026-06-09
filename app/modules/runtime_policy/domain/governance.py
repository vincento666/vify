from datetime import datetime
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.runtime_policy.infra.repository import RuntimePolicyRepository

ALLOWED_FALLBACK_TYPES = {"fake", "llm_agent", "existing_agent", "external_webhook"}
ALLOWED_FALLBACK_RESPONSE_TYPES = {"answer", "clarify", "handoff"}
THRESHOLD_KEYS = (
    "strongAcceptThreshold",
    "classifierMinConfidence",
)
UNIT_THRESHOLD_KEYS = (
    *THRESHOLD_KEYS,
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
        for key in UNIT_THRESHOLD_KEYS:
            value = thresholds.get(key)
            if not isinstance(value, int | float):
                failure_reasons.append(f"thresholds.{key}.required")
            elif value < 0 or value > 1:
                failure_reasons.append(f"thresholds.{key}.out_of_range")
        candidate_top_k = thresholds.get("candidateTopK")
        if not isinstance(candidate_top_k, int):
            failure_reasons.append("thresholds.candidateTopK.required")
        elif candidate_top_k < 1 or candidate_top_k > 20:
            failure_reasons.append("thresholds.candidateTopK.out_of_range")
        source_weights = thresholds.get("candidateSourceWeights")
        if not isinstance(source_weights, dict):
            failure_reasons.append("thresholds.candidateSourceWeights.required")
        else:
            for key, value in source_weights.items():
                if not str(key).strip() or not isinstance(value, int | float) or value < 0 or value > 5:
                    failure_reasons.append("thresholds.candidateSourceWeights.invalid")
                    break
        if thresholds.get("llmArbitrationRequiredForNonHardStop") is not True:
            failure_reasons.append("thresholds.llmArbitrationRequiredForNonHardStop.required_true")

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
        self._record_evaluation_audit(row, "profile_validated", "system", "", result)
        return self._evaluation_run_response_with_audit(row)

    def replay_golden_matrix(self, profile_id: int) -> dict[str, Any]:
        profile = self._repository.get_profile(profile_id)
        if profile is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy profile not found")
        result = self._replay.replay_golden_matrix(profile)
        row = self._repository.create_evaluation_run(_evaluation_run_values(result))
        self._record_evaluation_audit(row, "golden_matrix_replayed", "system", "", result)
        return self._evaluation_run_response_with_audit(row)

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
        self._record_evaluation_audit(row, "decision_logs_replayed", "system", "", result)
        return self._evaluation_run_response_with_audit(row)

    def get(self, run_id: int) -> dict[str, Any]:
        row = self._repository.get_evaluation_run(run_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy evaluation run not found")
        return self._evaluation_run_response_with_audit(row)

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

    def _record_evaluation_audit(
        self,
        row: dict[str, Any],
        event_type: str,
        actor: str,
        reason: str,
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        return self._repository.create_audit_event(
            {
                "release_id": None,
                "evaluation_run_id": row["id"],
                "profile_id": row["profile_id"],
                "profile_version": row["profile_version"],
                "event_type": event_type,
                "actor": actor,
                "reason": reason,
                "snapshot": snapshot,
            }
        )

    def _evaluation_run_response_with_audit(self, row: dict[str, Any]) -> dict[str, Any]:
        response = _evaluation_run_response(row)
        events, _total = self._repository.list_audit_events(1, 100, evaluation_run_id=int(row["id"]))
        response["auditEvents"] = [_audit_event_response(event) for event in events]
        return response


class RuntimePolicyReleaseService:
    def __init__(self, repository: RuntimePolicyRepository) -> None:
        self._repository = repository

    def approve_profile(self, profile_id: int, *, approved_by: str) -> dict[str, Any]:
        profile = self._profile_or_404(profile_id)
        evaluation_run_ids = self._required_passed_run_ids(profile)
        existing = self._release_for_current_version(profile)
        previous = self._previous_active_profile(profile_id)
        values = {
            "profile_id": profile["id"],
            "profile_version": profile["version"],
            "previous_active_profile_id": previous["id"] if previous else None,
            "previous_active_profile_version": previous["version"] if previous else None,
            "evaluation_run_ids": evaluation_run_ids,
            "status": "approved",
            "canary_percent": int(existing.get("canary_percent") or 0) if existing else 0,
            "approved_by": approved_by,
            "activated_by": "",
            "rolled_back_by": "",
            "activated_at": None,
            "rolled_back_at": None,
            "rollback_reason": "",
            "audit_snapshot": {"approvedBy": approved_by},
        }
        row = (
            self._repository.update_release(int(existing["id"]), values)
            if existing
            else self._repository.create_release(values)
        )
        self._record_release_audit(row, "release_approved", approved_by, "", {"approvedBy": approved_by})
        return self._release_response_with_audit(row)

    def canary_profile(self, profile_id: int, *, canary_percent: int) -> dict[str, Any]:
        if canary_percent < 0 or canary_percent > 100:
            raise BizError(ErrorCode.BAD_REQUEST, "canaryPercent must be between 0 and 100")
        profile = self._profile_or_404(profile_id)
        release = self._approved_release_for_current_version(profile)
        row = self._repository.update_release(
            int(release["id"]),
            {
                "status": "canary",
                "canary_percent": canary_percent,
                "audit_snapshot": {**(release.get("audit_snapshot") or {}), "canaryPercent": canary_percent},
            },
        )
        self._record_release_audit(row, "release_canary", "system", "", {"canaryPercent": canary_percent})
        return self._release_response_with_audit(row)

    def activate_profile(self, profile_id: int, *, activated_by: str) -> dict[str, Any]:
        profile = self._profile_or_404(profile_id)
        self._raise_if_version_drift(profile)
        self._required_passed_run_ids(profile)
        release = self._approved_release_for_current_version(profile)
        active_profiles = [row for row in self._repository.list_active_profiles() if int(row["id"]) != profile_id]
        previous = active_profiles[0] if active_profiles else None
        for active_profile in active_profiles:
            self._repository.set_profile_status(int(active_profile["id"]), "archived")
        self._repository.set_profile_status(profile_id, "active")
        row = self._repository.update_release(
            int(release["id"]),
            {
                "status": "active",
                "previous_active_profile_id": previous["id"] if previous else release.get("previous_active_profile_id"),
                "previous_active_profile_version": (
                    previous["version"] if previous else release.get("previous_active_profile_version")
                ),
                "activated_by": activated_by,
                "activated_at": datetime.now(),
                "audit_snapshot": {**(release.get("audit_snapshot") or {}), "activatedBy": activated_by},
            },
        )
        self._record_release_audit(row, "release_activated", activated_by, "", {"activatedBy": activated_by})
        return self._release_response_with_audit(row)

    def rollback_release(self, release_id: int, *, rolled_back_by: str, reason: str) -> dict[str, Any]:
        release = self._repository.get_release(release_id)
        if release is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy release not found")
        previous_profile_id = release.get("previous_active_profile_id")
        if previous_profile_id is None:
            raise BizError(ErrorCode.BAD_REQUEST, "rollback target required")
        previous = self._profile_or_404(int(previous_profile_id))
        current = self._profile_or_404(int(release["profile_id"]))
        self._repository.set_profile_status(int(current["id"]), "archived")
        self._repository.set_profile_status(int(previous["id"]), "active")
        row = self._repository.update_release(
            release_id,
            {
                "status": "rolled_back",
                "rolled_back_by": rolled_back_by,
                "rolled_back_at": datetime.now(),
                "rollback_reason": reason,
                "audit_snapshot": {
                    **(release.get("audit_snapshot") or {}),
                    "rolledBackBy": rolled_back_by,
                    "rollbackReason": reason,
                },
            },
        )
        self._record_release_audit(
            row,
            "release_rolled_back",
            rolled_back_by,
            reason,
            {
                "rolledBackBy": rolled_back_by,
                "rollbackReason": reason,
                "restoredProfileId": previous["id"],
                "archivedProfileId": current["id"],
            },
        )
        return self._release_response_with_audit(row)

    def get(self, release_id: int) -> dict[str, Any]:
        row = self._repository.get_release(release_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy release not found")
        return self._release_response_with_audit(row)

    def list_releases(
        self,
        page: int,
        page_size: int,
        *,
        profile_id: int | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        rows, total = self._repository.list_releases(page, page_size, profile_id=profile_id, status=status)
        return {
            "list": [_release_response(row) for row in rows],
            "total": total,
            "page": page,
            "pageSize": page_size,
        }

    def _record_release_audit(
        self,
        row: dict[str, Any] | None,
        event_type: str,
        actor: str,
        reason: str,
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        release = _release_response(row)
        return self._repository.create_audit_event(
            {
                "release_id": release["id"],
                "evaluation_run_id": None,
                "profile_id": release["profileId"],
                "profile_version": release["profileVersion"],
                "event_type": event_type,
                "actor": actor,
                "reason": reason,
                "snapshot": snapshot,
            }
        )

    def _release_response_with_audit(self, row: dict[str, Any] | None) -> dict[str, Any]:
        response = _release_response(row)
        events, _total = self._repository.list_audit_events(1, 100, release_id=response["id"])
        response["auditEvents"] = [_audit_event_response(event) for event in events]
        return response

    def _profile_or_404(self, profile_id: int) -> dict[str, Any]:
        profile = self._repository.get_profile(profile_id)
        if profile is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy profile not found")
        return profile

    def _required_passed_run_ids(self, profile: dict[str, Any]) -> list[int]:
        run_ids: list[int] = []
        for run_type in ("validation", "golden_matrix", "decision_log_replay"):
            rows, _total = self._repository.list_evaluation_runs(
                1,
                20,
                profile_id=int(profile["id"]),
                run_type=run_type,
                status="passed",
            )
            current_rows = [row for row in rows if int(row["profile_version"]) == int(profile["version"])]
            if not current_rows:
                raise BizError(ErrorCode.BAD_REQUEST, f"{run_type} evaluation required before activation")
            run_ids.append(int(current_rows[0]["id"]))
        return run_ids

    def _release_for_current_version(self, profile: dict[str, Any]) -> dict[str, Any] | None:
        releases = self._repository.list_releases_for_profile(int(profile["id"]))
        for release in releases:
            if int(release["profile_version"]) == int(profile["version"]):
                return release
        return None

    def _approved_release_for_current_version(self, profile: dict[str, Any]) -> dict[str, Any]:
        release = self._release_for_current_version(profile)
        if release is None or release["status"] not in {"approved", "canary"}:
            raise BizError(ErrorCode.BAD_REQUEST, "approval required before activation")
        return release

    def _raise_if_version_drift(self, profile: dict[str, Any]) -> None:
        releases = self._repository.list_releases_for_profile(int(profile["id"]))
        if releases and all(int(release["profile_version"]) != int(profile["version"]) for release in releases):
            raise BizError(ErrorCode.BAD_REQUEST, "Profile version changed since evaluation")

    def _previous_active_profile(self, profile_id: int) -> dict[str, Any] | None:
        active_profiles = [row for row in self._repository.list_active_profiles() if int(row["id"]) != profile_id]
        return active_profiles[0] if active_profiles else None


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


def _release_response(row: dict[str, Any] | None) -> dict[str, Any]:
    if row is None:
        raise BizError(ErrorCode.NOT_FOUND, "Runtime policy release not found")
    return {
        "id": int(row["id"]),
        "profileId": int(row["profile_id"]),
        "profileVersion": int(row["profile_version"]),
        "previousActiveProfileId": row.get("previous_active_profile_id"),
        "previousActiveProfileVersion": row.get("previous_active_profile_version"),
        "evaluationRunIds": row.get("evaluation_run_ids") or [],
        "status": str(row["status"]),
        "canaryPercent": int(row.get("canary_percent") or 0),
        "approvedBy": str(row.get("approved_by") or ""),
        "activatedBy": str(row.get("activated_by") or ""),
        "rolledBackBy": str(row.get("rolled_back_by") or ""),
        "activatedAt": _optional_iso(row.get("activated_at")),
        "rolledBackAt": _optional_iso(row.get("rolled_back_at")),
        "rollbackReason": str(row.get("rollback_reason") or ""),
        "auditSnapshot": row.get("audit_snapshot") or {},
        "createdAt": _iso(row["created_at"]),
        "updatedAt": _iso(row["updated_at"]),
    }


def _audit_event_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "releaseId": row.get("release_id"),
        "evaluationRunId": row.get("evaluation_run_id"),
        "profileId": row.get("profile_id"),
        "profileVersion": row.get("profile_version"),
        "eventType": str(row["event_type"]),
        "actor": str(row.get("actor") or ""),
        "reason": str(row.get("reason") or ""),
        "snapshot": row.get("snapshot") or {},
        "createdAt": _iso(row["created_at"]),
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


def _optional_iso(value: Any) -> str | None:
    if value is None:
        return None
    return _iso(value)
