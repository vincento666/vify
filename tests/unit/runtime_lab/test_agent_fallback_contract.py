import unittest

from app.modules.runtime_lab.domain.payload import format_route_decision
from app.modules.runtime_lab.domain.router import RouteDecision


class AgentFallbackContractTest(unittest.TestCase):
    def test_agent_fallback_route_decision_payload_exposes_policy_evidence(self) -> None:
        payload = format_route_decision(
            RouteDecision(
                action="AGENT_FALLBACK",
                reason="Controlled fallback Agent answered unresolved user request",
                agent_answer={
                    "sourceLayer": "agent_policy",
                    "reasonCode": "AGENT_ANSWER",
                    "responseType": "answer",
                    "answer": "我可以先帮您整理诉求，再转给对应柜台确认。",
                    "confidence": 0.72,
                    "mutatesSopState": False,
                    "policyEvidence": {"accepted": True},
                },
            )
        )

        self.assertEqual(payload["action"], "AGENT_FALLBACK")
        self.assertEqual(payload["agentAnswer"]["sourceLayer"], "agent_policy")
        self.assertEqual(payload["agentAnswer"]["reasonCode"], "AGENT_ANSWER")
        self.assertFalse(payload["agentAnswer"]["mutatesSopState"])
        self.assertEqual(payload["finalDecision"]["sourceLayer"], "agent_policy")
        self.assertEqual(payload["finalDecision"]["reasonCode"], "AGENT_ANSWER")

    def test_fake_fallback_agent_returns_deterministic_answer(self) -> None:
        from app.modules.runtime_lab.domain.agent_fallback import FallbackAgentRequest, FakeFallbackAgent

        result = FakeFallbackAgent().run(
            FallbackAgentRequest(
                message="机场大巴末班车几点？",
                active_task=None,
                suspended_tasks=[],
                recent_events=[],
            )
        )

        self.assertEqual(result.response_type, "answer")
        self.assertIn("机场大巴末班车几点", result.answer)
        self.assertFalse(result.proposed_actions)

    def test_fake_fallback_agent_can_recommend_handoff_for_complex_disputes(self) -> None:
        from app.modules.runtime_lab.domain.agent_fallback import FallbackAgentRequest, FakeFallbackAgent

        result = FakeFallbackAgent().run(
            FallbackAgentRequest(
                message="航司系统异常需要进一步判断",
                active_task=None,
                suspended_tasks=[],
                recent_events=[],
            )
        )

        self.assertEqual(result.response_type, "handoff_recommendation")
        self.assertIn("进一步判断", result.handoff_reason)
