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


class RuntimePolicyEvaluationRunService:
    def __init__(self, repository: RuntimePolicyRepository) -> None:
        self._repository = repository
        self._validator = RuntimePolicyValidationService()

    def validate_profile(self, profile_id: int) -> dict[str, Any]:
        profile = self._repository.get_profile(profile_id)
        if profile is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy profile not found")
        result = self._validator.validate_profile_row(profile)
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
    return {
        "profile_id": validation_result["profileId"],
        "profile_version": validation_result["profileVersion"],
        "run_type": validation_result["runType"],
        "status": validation_result["status"],
        "input_snapshot": validation_result["inputSnapshot"],
        "result": {
            "passed": validation_result["passed"],
            "failureReasons": validation_result["failureReasons"],
        },
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


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
