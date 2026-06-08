from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from app.modules.runtime_lab.domain.router import RouteDecision

AgentResponseType = Literal["answer", "clarification", "handoff_recommendation"]

FORBIDDEN_AGENT_ACTIONS = {
    "START_SOP",
    "SUSPEND_AND_START",
    "RESUME_TASK",
    "CONTINUE_ACTIVE_SOP",
    "COMPLETE_TASK",
    "HANDOFF_TO_HUMAN",
}


@dataclass(frozen=True)
class FallbackAgentRequest:
    message: str
    active_task: dict[str, Any] | None
    suspended_tasks: list[dict[str, Any]]
    recent_events: list[dict[str, Any]]


@dataclass(frozen=True)
class FallbackAgentOutput:
    response_type: AgentResponseType
    answer: str = ""
    clarification_question: str = ""
    handoff_reason: str = ""
    confidence: float = 0.0
    citations: list[dict[str, Any]] = field(default_factory=list)
    safety_flags: list[str] = field(default_factory=list)
    proposed_actions: list[str] = field(default_factory=list)


class FallbackAgentPort(Protocol):
    def run(self, request: FallbackAgentRequest) -> FallbackAgentOutput:
        ...


class FakeFallbackAgent:
    def run(self, request: FallbackAgentRequest) -> FallbackAgentOutput:
        message = request.message.strip()
        if _looks_unclear(message):
            return FallbackAgentOutput(
                response_type="clarification",
                clarification_question="请补充您要咨询的问题背景，或说明希望办理的业务。",
                confidence=0.5,
            )
        if _looks_like_complex_handoff(message):
            return FallbackAgentOutput(
                response_type="handoff_recommendation",
                answer="该问题需要人工客服进一步判断。",
                handoff_reason=f"Fallback Agent judged this request needs further human review: {message}",
                confidence=0.78,
            )
        return FallbackAgentOutput(
            response_type="answer",
            answer=f"我先帮您整理诉求：{message}。该问题未匹配到标准办理流程，建议以机场或航司官方信息为准。",
            confidence=0.68,
        )


class AgentOutputPolicy:
    def __init__(self, *, max_clarification_attempts: int = 2) -> None:
        self.max_clarification_attempts = max_clarification_attempts

    def decide(
        self,
        output: FallbackAgentOutput,
        *,
        clarification_attempts: int,
    ) -> RouteDecision:
        unsafe_actions = [action for action in output.proposed_actions if action in FORBIDDEN_AGENT_ACTIONS]
        if unsafe_actions:
            return RouteDecision(
                action="CLARIFY",
                reason="Fallback Agent proposed unsupported runtime side effects",
                agent_answer=_agent_answer_payload(
                    output,
                    reason_code="AGENT_UNSUPPORTED_SIDE_EFFECT",
                    policy_evidence={"accepted": False, "rejectedActions": unsafe_actions},
                ),
            )
        if output.response_type == "answer":
            return RouteDecision(
                action="AGENT_FALLBACK",
                reason="Controlled fallback Agent answered unresolved user request",
                agent_answer=_agent_answer_payload(
                    output,
                    reason_code="AGENT_ANSWER",
                    policy_evidence={"accepted": True},
                ),
            )
        if output.response_type == "clarification":
            if clarification_attempts >= self.max_clarification_attempts:
                return _agent_handoff_decision(output, "CLARIFICATION_FAILED", "Repeated fallback Agent clarification failed")
            return RouteDecision(
                action="CLARIFY",
                reason="Fallback Agent requested clarification",
                agent_answer=_agent_answer_payload(
                    output,
                    reason_code="AGENT_CLARIFICATION",
                    policy_evidence={
                        "accepted": True,
                        "clarificationAttempt": clarification_attempts + 1,
                        "maxClarificationAttempts": self.max_clarification_attempts,
                    },
                ),
            )
        if output.response_type == "handoff_recommendation":
            return _agent_handoff_decision(
                output,
                "AGENT_RECOMMENDED_HANDOFF",
                output.handoff_reason or "Fallback Agent recommended handoff",
            )
        return RouteDecision(
            action="CLARIFY",
            reason="Fallback Agent returned unsupported response type",
            agent_answer=_agent_answer_payload(
                output,
                reason_code="AGENT_UNSUPPORTED_RESPONSE",
                policy_evidence={"accepted": False},
            ),
        )


def _agent_answer_payload(
    output: FallbackAgentOutput,
    *,
    reason_code: str,
    policy_evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "sourceLayer": "agent_policy",
        "reasonCode": reason_code,
        "responseType": output.response_type,
        "answer": output.answer,
        "clarificationQuestion": output.clarification_question,
        "handoffReason": output.handoff_reason,
        "confidence": output.confidence,
        "citations": list(output.citations),
        "safetyFlags": list(output.safety_flags),
        "proposedActions": list(output.proposed_actions),
        "mutatesSopState": False,
        "policyEvidence": policy_evidence,
    }


def _agent_handoff_decision(output: FallbackAgentOutput, reason_code: str, reason: str) -> RouteDecision:
    return RouteDecision(
        action="HANDOFF_TO_HUMAN",
        reason=reason,
        agent_answer=_agent_answer_payload(
            output,
            reason_code=reason_code,
            policy_evidence={"accepted": True, "finalAuthority": "policy_gate"},
        ),
        handoff={
            "sourceLayer": "agent_policy",
            "reasonCode": reason_code,
            "matchedTerms": [],
            "routeEvidence": {
                "agentResponseType": output.response_type,
                "confidence": output.confidence,
                "handoffReason": output.handoff_reason,
                "finalAuthority": "policy_gate",
            },
        },
    )


def _looks_unclear(message: str) -> bool:
    normalized = message.strip()
    return normalized in {"", "?", "？", "那现在怎么办", "不知道", "还是那个", "随便"} or len(normalized) <= 3


def _looks_like_complex_handoff(message: str) -> bool:
    return any(term in message for term in ("争议", "复杂", "进一步判断", "系统异常", "无法处理"))
