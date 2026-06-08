import unittest

from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, ScoreBreakdown
from app.modules.runtime_lab.domain.classifier import ClassifierInput, FakeConstrainedIntentClassifier
from app.modules.runtime_lab.domain.payload import format_route_decision
from app.modules.runtime_lab.domain.policy import PolicyGate
from app.modules.runtime_lab.domain.router import RouteDecision


class HandoffActionContractTest(unittest.TestCase):
    def test_handoff_candidate_serializes_as_first_class_route_candidate(self) -> None:
        candidate = _handoff_candidate()

        self.assertEqual(candidate.candidate_type, CandidateType.HANDOFF_TO_HUMAN)
        self.assertEqual(candidate.to_dict()["candidate_type"], "HANDOFF_TO_HUMAN")
        self.assertEqual(candidate.to_dict()["target_id"], "USER_REQUEST")

    def test_classifier_can_select_handoff_inside_finite_allowed_actions(self) -> None:
        candidate = _handoff_candidate()
        result = FakeConstrainedIntentClassifier().classify(
            ClassifierInput(
                message="我要人工客服",
                session_state={"activeTask": False, "suspendedTaskCount": 0},
                candidates=(candidate,),
                allowed_actions=("HANDOFF_TO_HUMAN", "CLARIFY"),
                thresholds={"classifierMinConfidence": 0.6},
            )
        )

        self.assertEqual(result.selected_action, "HANDOFF_TO_HUMAN")
        self.assertEqual(result.selected_candidate_id, "handoff:USER_REQUEST")
        self.assertFalse(result.needs_clarification)

    def test_policy_gate_returns_handoff_decision_without_sop_mutation_fields(self) -> None:
        decision = PolicyGate(_Interruptible()).pre_classifier_decision(
            [_handoff_candidate(matched_terms=("人工客服", "转人工"))],
            active_task={"id": 7, "sop_id": "refund_ticket", "current_step": "collect_order_no"},
            suspended_count=1,
        )

        assert decision is not None
        self.assertEqual(decision.action, "HANDOFF_TO_HUMAN")
        self.assertIsNone(decision.target_sop_id)
        self.assertIsNone(decision.active_task_id)
        self.assertEqual(decision.handoff["sourceLayer"], "explicit_signal")
        self.assertEqual(decision.handoff["reasonCode"], "USER_REQUEST")
        self.assertEqual(decision.handoff["matchedTerms"], ["人工客服", "转人工"])

    def test_route_decision_payload_exposes_normalized_handoff_evidence(self) -> None:
        payload = format_route_decision(
            RouteDecision(
                action="HANDOFF_TO_HUMAN",
                reason="User asked for human support",
                handoff={
                    "sourceLayer": "explicit_signal",
                    "reasonCode": "USER_REQUEST",
                    "matchedTerms": ["人工客服"],
                    "routeEvidence": {"candidateId": "handoff:USER_REQUEST"},
                },
            )
        )

        self.assertEqual(payload["action"], "HANDOFF_TO_HUMAN")
        self.assertEqual(payload["handoff"]["sourceLayer"], "explicit_signal")
        self.assertEqual(payload["handoff"]["reasonCode"], "USER_REQUEST")
        self.assertEqual(payload["handoff"]["routeEvidence"]["candidateId"], "handoff:USER_REQUEST")
        self.assertEqual(payload["finalDecision"]["action"], "HANDOFF_TO_HUMAN")


def _handoff_candidate(matched_terms: tuple[str, ...] = ("人工客服",)) -> RouteCandidate:
    return RouteCandidate(
        candidate_id="handoff:USER_REQUEST",
        candidate_type=CandidateType.HANDOFF_TO_HUMAN,
        target_id="USER_REQUEST",
        display_name="转人工",
        source="explicit_signal",
        score=1.0,
        score_breakdown=ScoreBreakdown(keyword=1.0, alias=0.0, semantic=0.0),
        matched_terms=matched_terms,
        risk_level="HIGH",
        requires_classifier=False,
        reason="Explicit handoff trigger",
    )


class _Interruptible:
    def is_interruptible(self, _sop_id: str, _step_id: str) -> bool:
        return True
