import unittest
from unittest.mock import MagicMock, patch

from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, ScoreBreakdown
from app.modules.runtime_lab.domain.classifier import ClassifierInput, ClassifierResult
from app.modules.runtime_lab.domain.service import RuntimeLabService


class CandidateMarginPolicyTest(unittest.TestCase):
    def test_default_low_post_fusion_margin_clarifies_before_classifier_or_mutation(self) -> None:
        classifier = _RecordingClassifier()
        adapter = MagicMock()
        service = RuntimeLabService(MagicMock(), classifier=classifier, adapter=adapter)

        with (
            patch.object(service._explicit_signals, "detect", return_value=[_candidate("refund_ticket", 0.90)]),
            patch.object(service._semantic_recall, "recall", return_value=[_candidate("change_flight", 0.85)]),
        ):
            decision = service.preview_route("我想办理机票业务")

        self.assertEqual(decision.action, "CLARIFY")
        self.assertEqual(classifier.inputs, [])
        adapter.start.assert_not_called()
        margin = decision.policy_gate["candidateMargin"]
        self.assertEqual(margin["topCandidateId"], "sop:refund_ticket")
        self.assertEqual(margin["secondCandidateId"], "sop:change_flight")
        self.assertEqual(margin["value"], 0.05)
        self.assertEqual(margin["threshold"], 0.12)
        self.assertEqual(margin["outcome"], "CLARIFY")

    def test_sole_viable_candidate_does_not_clarify_for_absent_second_score(self) -> None:
        classifier = _RecordingClassifier()
        service = RuntimeLabService(MagicMock(), classifier=classifier)

        with (
            patch.object(service._explicit_signals, "detect", return_value=[_candidate("refund_ticket", 0.90)]),
            patch.object(service._semantic_recall, "recall", return_value=[]),
        ):
            decision = service.preview_route("我想办理退票")

        self.assertEqual(decision.action, "START_SOP")
        self.assertEqual(len(classifier.inputs), 1)
        self.assertEqual(decision.policy_gate["candidateMargin"]["outcome"], "NOT_APPLICABLE_SINGLE_CANDIDATE")


class _RecordingClassifier:
    def __init__(self) -> None:
        self.inputs: list[ClassifierInput] = []

    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        self.inputs.append(classifier_input)
        candidate = classifier_input.candidates[0]
        return ClassifierResult(
            selected_action="START_SOP",
            selected_candidate_id=candidate.candidate_id,
            confidence=0.95,
            rationale="margin fixture classifier",
            needs_clarification=False,
            clarification_question=None,
        )


def _candidate(target_id: str, score: float) -> RouteCandidate:
    return RouteCandidate(
        candidate_id=f"sop:{target_id}",
        candidate_type=CandidateType.SOP_INTENT,
        target_id=target_id,
        display_name=target_id,
        source="margin_fixture",
        score=score,
        score_breakdown=ScoreBreakdown(keyword=score, alias=0.0, semantic=0.0),
        matched_terms=(target_id,),
        risk_level="LOW",
        requires_classifier=True,
        reason="candidate margin fixture",
    )
