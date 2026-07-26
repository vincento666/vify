import unittest

from app.modules.runtime_lab.domain.payload import format_route_decision
from app.modules.runtime_lab.domain.router import RouteDecision


class TargetedClarificationProjectionTest(unittest.TestCase):
    def test_route_decision_projects_additive_targeted_question(self) -> None:
        decision = RouteDecision(
            action="CLARIFY",
            reason="Classifier requested clarification",
            clarification_question="请确认您要退整张机票，还是只退附加服务？",
        )

        payload = format_route_decision(decision)

        self.assertEqual(
            payload["clarificationQuestion"],
            "请确认您要退整张机票，还是只退附加服务？",
        )

    def test_non_clarification_decision_projects_nullable_question(self) -> None:
        payload = format_route_decision(
            RouteDecision(
                action="START_SOP",
                reason="Matched",
                target_sop_id="refund_ticket",
            )
        )

        self.assertIsNone(payload["clarificationQuestion"])


if __name__ == "__main__":
    unittest.main()
