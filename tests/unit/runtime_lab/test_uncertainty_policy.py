import math
import unittest

from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, ScoreBreakdown
from app.modules.runtime_lab.domain.classifier import (
    ClassifierInput,
    ClassifierResult,
    UncertaintyPolicy,
)


class UncertaintyPolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        self._input = ClassifierInput(
            message="我要退票",
            session_state={"activeTask": False},
            candidates=(
                RouteCandidate(
                    candidate_id="sop:refund_ticket",
                    candidate_type=CandidateType.SOP_INTENT,
                    target_id="refund_ticket",
                    display_name="退票",
                    source="test",
                    score=0.88,
                    score_breakdown=ScoreBreakdown(keyword=0.88, alias=0.0, semantic=0.0),
                    matched_terms=("退票",),
                    risk_level="LOW",
                    requires_classifier=True,
                    reason="test",
                ),
            ),
            allowed_actions=("START_SOP", "CLARIFY"),
            thresholds={"classifierMinConfidence": 0.6},
        )
        self._policy = UncertaintyPolicy()

    def test_preserves_a_finite_coherent_selection(self) -> None:
        result = _result()

        enforced = self._policy.enforce(result, self._input)

        self.assertIs(enforced, result)

    def test_uncertain_or_incoherent_results_are_normalized_to_clarify(self) -> None:
        cases = {
            "below threshold": _result(confidence=0.59),
            "not finite": _result(confidence=math.nan),
            "not numeric": _result(confidence="invalid"),
            "negative": _result(confidence=-0.1),
            "above one": _result(confidence=1.1),
            "explicit clarification": _result(
                needs_clarification=True,
                clarification_question="请确认是否退票",
            ),
            "outside candidate pool": _result(selected_candidate_id="sop:invented"),
            "clarify marked certain": _result(
                selected_action="CLARIFY",
                selected_candidate_id=None,
                needs_clarification=False,
            ),
        }

        for name, result in cases.items():
            with self.subTest(name=name):
                enforced = self._policy.enforce(result, self._input)

                self.assertEqual(enforced.selected_action, "CLARIFY")
                self.assertIsNone(enforced.selected_candidate_id)
                self.assertTrue(enforced.needs_clarification)
                self.assertTrue(math.isfinite(enforced.confidence))

    def test_clarification_question_is_stripped_bounded_and_has_a_fallback(self) -> None:
        normalized = self._policy.enforce(
            _result(
                needs_clarification=True,
                clarification_question=f"  {'请补充 ' * 80}  ",
            ),
            self._input,
        )
        fallback = self._policy.enforce(
            _result(needs_clarification=True, clarification_question=" \n\t "),
            self._input,
        )

        question = normalized.clarification_question
        self.assertIsNotNone(question)
        assert question is not None
        self.assertEqual(question, question.strip())
        self.assertLessEqual(len(question), 256)
        self.assertTrue(fallback.clarification_question)


def _result(
    *,
    selected_action: str = "START_SOP",
    selected_candidate_id: str | None = "sop:refund_ticket",
    confidence: object = 0.88,
    needs_clarification: bool = False,
    clarification_question: str | None = None,
) -> ClassifierResult:
    return ClassifierResult(
        selected_action=selected_action,
        selected_candidate_id=selected_candidate_id,
        confidence=confidence,  # type: ignore[arg-type]
        rationale="scripted real classifier",
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
        arbitrator_mode="llm",
        used_real_llm=True,
    )


if __name__ == "__main__":
    unittest.main()
