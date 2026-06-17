from enum import StrEnum

from app.modules.ai_assistant.domain.tools import RiskLevel


class ApprovalMode(StrEnum):
    ASK_EACH_TIME = "ask_each_time"
    SMART_APPROVAL = "smart_approval"
    ALWAYS_APPROVE = "always_approve"


class PermissionDecision(StrEnum):
    AUTO_APPROVE = "AUTO_APPROVE"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"


class ApprovalPolicy:
    def __init__(self, environment: str = "test") -> None:
        self._environment = environment.strip().lower()

    def decide(self, *, approval_mode: ApprovalMode, risk_level: RiskLevel) -> PermissionDecision:
        if approval_mode == ApprovalMode.ALWAYS_APPROVE and self._environment in {"prod", "production"}:
            return PermissionDecision.DENY
        if approval_mode == ApprovalMode.ALWAYS_APPROVE:
            return PermissionDecision.AUTO_APPROVE
        if risk_level == RiskLevel.READ and approval_mode == ApprovalMode.SMART_APPROVAL:
            return PermissionDecision.AUTO_APPROVE
        return PermissionDecision.REQUIRE_APPROVAL
