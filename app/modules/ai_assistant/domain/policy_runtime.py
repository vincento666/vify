from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.ai_assistant.domain.permissions import ApprovalMode, ApprovalPolicy, PermissionDecision
from app.modules.ai_assistant.domain.tools import RiskLevel, ToolManifest


@dataclass(frozen=True)
class PermissionPolicyRule:
    rule_id: str
    match: dict[str, Any]
    effect: str
    reason: str
    budget_limit: int | None = None


@dataclass(frozen=True)
class PermissionEvaluation:
    decision: PermissionDecision
    matched_rule_id: str
    reason: str
    event: dict[str, Any]


class SessionPermissionPolicy:
    def __init__(
        self,
        *,
        default_decision: str = "legacy",
        rules: list[PermissionPolicyRule] | None = None,
        environment: str = "test",
    ) -> None:
        self.default_decision = default_decision
        self.rules = list(rules or [])
        self._legacy = ApprovalPolicy(environment=environment)

    @classmethod
    def from_context(cls, context: dict[str, Any] | None, *, environment: str = "test") -> SessionPermissionPolicy:
        raw_policy = (context or {}).get("aiAssistantPolicy")
        if not isinstance(raw_policy, dict):
            return cls(environment=environment)
        rules: list[PermissionPolicyRule] = []
        for index, raw_rule in enumerate(raw_policy.get("rules") or []):
            if not isinstance(raw_rule, dict):
                continue
            rules.append(
                PermissionPolicyRule(
                    rule_id=str(raw_rule.get("id") or raw_rule.get("ruleId") or f"rule-{index + 1}"),
                    match=dict(raw_rule.get("match") or {}),
                    effect=str(raw_rule.get("effect") or "require_approval"),
                    reason=str(raw_rule.get("reason") or "session policy matched"),
                    budget_limit=_optional_int(raw_rule.get("budgetLimit")),
                )
            )
        return cls(
            default_decision=str(raw_policy.get("defaultDecision") or "legacy"),
            rules=rules,
            environment=environment,
        )

    def evaluate(
        self,
        *,
        session_id: int,
        run_id: int,
        tool_name: str,
        manifest: ToolManifest,
        tool_input: dict[str, Any],
        approval_mode: ApprovalMode,
        current_budget: int | None = None,
    ) -> PermissionEvaluation:
        matched = [rule for rule in self.rules if _rule_matches(rule, tool_name, manifest, tool_input)]
        rule = _highest_precedence_rule(matched)
        if rule is not None:
            budget_exceeded = rule.budget_limit is not None and current_budget is not None and current_budget > rule.budget_limit
            decision = PermissionDecision.DENY if budget_exceeded else _decision_from_effect(rule.effect)
            matched_rule_id = rule.rule_id
            reason = "budget limit exceeded" if budget_exceeded else rule.reason
        else:
            decision = _default_decision(
                self.default_decision,
                legacy=self._legacy,
                approval_mode=approval_mode,
                risk_level=manifest.risk_level,
            )
            matched_rule_id = "default"
            reason = f"default:{self.default_decision}"
        payload = {
            "sessionId": session_id,
            "runId": run_id,
            "toolName": tool_name,
            "riskLevel": manifest.risk_level.value,
            "approvalMode": approval_mode.value,
            "decision": _decision_value(decision),
            "matchedRuleId": matched_rule_id,
            "reason": reason,
        }
        if rule is not None and rule.budget_limit is not None:
            payload["budgetLimit"] = rule.budget_limit
            payload["currentBudget"] = current_budget
        return PermissionEvaluation(
            decision=decision,
            matched_rule_id=matched_rule_id,
            reason=reason,
            event={"type": "permission.evaluated", "payload": payload},
        )


def _rule_matches(rule: PermissionPolicyRule, tool_name: str, manifest: ToolManifest, tool_input: dict[str, Any]) -> bool:
    match = rule.match
    if _expected(match, "tool") and str(match["tool"]) != tool_name:
        return False
    if _expected(match, "risk") and str(match["risk"]) != manifest.risk_level.value:
        return False
    if _expected(match, "path"):
        raw_path = str(tool_input.get("path") or "")
        if str(match["path"]) != raw_path:
            return False
    if _expected(match, "command"):
        raw_command = str(tool_input.get("command") or "")
        if str(match["command"]) != raw_command:
            return False
    if _expected(match, "externalSideEffect"):
        expected = bool(match["externalSideEffect"])
        actual = manifest.risk_level == RiskLevel.EXTERNAL_SIDE_EFFECT
        if expected != actual:
            return False
    return True


def _highest_precedence_rule(rules: list[PermissionPolicyRule]) -> PermissionPolicyRule | None:
    if not rules:
        return None
    precedence = {"deny": 3, "require_approval": 2, "allow": 1}
    return sorted(rules, key=lambda rule: precedence.get(rule.effect, 2), reverse=True)[0]


def _decision_from_effect(effect: str) -> PermissionDecision:
    normalized = effect.strip().lower()
    if normalized == "allow":
        return PermissionDecision.AUTO_APPROVE
    if normalized == "deny":
        return PermissionDecision.DENY
    return PermissionDecision.REQUIRE_APPROVAL


def _default_decision(
    default_decision: str,
    *,
    legacy: ApprovalPolicy,
    approval_mode: ApprovalMode,
    risk_level: RiskLevel,
) -> PermissionDecision:
    normalized = default_decision.strip().lower()
    if normalized == "allow":
        return PermissionDecision.AUTO_APPROVE
    if normalized == "deny":
        return PermissionDecision.DENY
    if normalized == "require_approval":
        if risk_level == RiskLevel.READ and approval_mode == ApprovalMode.SMART_APPROVAL:
            return PermissionDecision.AUTO_APPROVE
        return PermissionDecision.REQUIRE_APPROVAL
    return legacy.decide(approval_mode=approval_mode, risk_level=risk_level)


def _decision_value(decision: PermissionDecision) -> str:
    if decision == PermissionDecision.AUTO_APPROVE:
        return "allow"
    if decision == PermissionDecision.DENY:
        return "deny"
    return "require_approval"


def _expected(match: dict[str, Any], key: str) -> bool:
    return key in match and match[key] not in (None, "")


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)
