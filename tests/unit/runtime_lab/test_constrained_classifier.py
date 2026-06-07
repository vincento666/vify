import json
import unittest

from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, ScoreBreakdown
from app.modules.runtime_lab.domain.classifier import (
    ClassifierInput,
    ClassifierResult,
    FakeConstrainedIntentClassifier,
)


class ConstrainedClassifierTest(unittest.TestCase):
    def test_classifier_input_serializes_json_like_without_faq_or_rag_snippets(self) -> None:
        classifier_input = ClassifierInput(
            message="我想退费",
            session_state={"sessionId": 1, "status": "ACTIVE"},
            candidates=(_candidate("sop:refund_ticket", "refund_ticket", 0.78),),
            allowed_actions=("START_SOP", "CLARIFY"),
            thresholds={"semanticAccept": 0.78},
        )

        payload = classifier_input.to_dict()

        json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("faqCandidates", payload)
        self.assertNotIn("ragSnippets", payload)
        self.assertEqual(payload["candidates"][0]["candidate_id"], "sop:refund_ticket")

    def test_rejects_classifier_result_that_selects_candidate_outside_finite_set(self) -> None:
        classifier = FakeConstrainedIntentClassifier(
            scripted_result=ClassifierResult(
                selected_action="START_SOP",
                selected_candidate_id="sop:invented",
                confidence=0.9,
                rationale="invented",
                needs_clarification=False,
                clarification_question=None,
            )
        )

        with self.assertRaises(ValueError):
            classifier.classify(_input())

    def test_rejects_classifier_result_action_outside_allowed_enum(self) -> None:
        classifier = FakeConstrainedIntentClassifier(
            scripted_result=ClassifierResult(
                selected_action="ANSWER_RAG",
                selected_candidate_id=None,
                confidence=0.9,
                rationale="future action",
                needs_clarification=False,
                clarification_question=None,
            )
        )

        with self.assertRaises(ValueError):
            classifier.classify(_input())

    def test_low_confidence_candidate_returns_clarification(self) -> None:
        result = FakeConstrainedIntentClassifier().classify(
            ClassifierInput(
                message="随便问问",
                session_state={"sessionId": 1},
                candidates=(_candidate("sop:refund_ticket", "refund_ticket", 0.4),),
                allowed_actions=("START_SOP", "CLARIFY"),
                thresholds={"classifierMinConfidence": 0.6},
            )
        )

        self.assertEqual(result.selected_action, "CLARIFY")
        self.assertIsNone(result.selected_candidate_id)
        self.assertTrue(result.needs_clarification)
        self.assertIsNotNone(result.clarification_question)


def _input() -> ClassifierInput:
    return ClassifierInput(
        message="我想退费",
        session_state={"sessionId": 1},
        candidates=(_candidate("sop:refund_ticket", "refund_ticket", 0.78),),
        allowed_actions=("START_SOP", "CLARIFY"),
        thresholds={"classifierMinConfidence": 0.6},
    )


def _candidate(candidate_id: str, target_id: str, score: float) -> RouteCandidate:
    return RouteCandidate(
        candidate_id=candidate_id,
        candidate_type=CandidateType.SOP_INTENT,
        target_id=target_id,
        display_name=target_id,
        source="test",
        score=score,
        score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=score),
        matched_terms=("退费",),
        risk_level="LOW",
        requires_classifier=True,
        reason="test",
    )
