import json
import unittest

from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, ScoreBreakdown
import app.modules.runtime_lab.domain.classifier as classifier_module
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

    def test_fake_classifier_result_reports_arbitrator_mode_without_real_llm(self) -> None:
        result = FakeConstrainedIntentClassifier().classify(_input())

        payload = result.to_dict()

        self.assertEqual(payload["arbitrator_mode"], "fake")
        self.assertFalse(payload["used_real_llm"])

    def test_llm_classifier_uses_external_arbitrator_inside_finite_candidate_contract(self) -> None:
        captured_payloads: list[dict[str, object]] = []

        def complete(payload: dict[str, object]) -> dict[str, object]:
            captured_payloads.append(payload)
            return {
                "selected_action": "START_SOP",
                "selected_candidate_id": "sop:refund_ticket",
                "confidence": 0.92,
                "rationale": "用户表达票款退回诉求，命中有限候选中的退票 SOP",
                "needs_clarification": False,
                "clarification_question": None,
            }

        classifier = classifier_module.LlmConstrainedIntentClassifier(complete)
        result = classifier.classify(_input())

        self.assertEqual(result.selected_action, "START_SOP")
        self.assertEqual(result.selected_candidate_id, "sop:refund_ticket")
        self.assertEqual(result.arbitrator_mode, "llm")
        self.assertTrue(result.used_real_llm)
        self.assertEqual(captured_payloads[0]["allowedActions"], ["START_SOP", "CLARIFY"])
        self.assertEqual(
            [candidate["candidate_id"] for candidate in captured_payloads[0]["candidates"]],
            ["sop:refund_ticket"],
        )

    def test_llm_classifier_payload_is_compact_and_excludes_full_candidate_debug_fields(self) -> None:
        captured_payloads: list[dict[str, object]] = []

        def complete(payload: dict[str, object]) -> dict[str, object]:
            captured_payloads.append(payload)
            return {
                "selected_action": "START_SOP",
                "selected_candidate_id": "sop:refund_ticket",
                "confidence": 0.92,
                "rationale": "退费诉求匹配退票候选",
                "needs_clarification": False,
                "clarification_question": None,
            }

        classifier = classifier_module.LlmConstrainedIntentClassifier(complete)
        classifier.classify(
            ClassifierInput(
                message="我想退费",
                session_state={
                    "activeTask": True,
                    "activeTaskId": 9,
                    "activeSopId": "flight_booking",
                    "suspendedTaskCount": 0,
                    "enabledSopIds": ["flight_booking", "refund_ticket", "change_flight"],
                },
                candidates=(
                    _candidate("sop:refund_ticket", "refund_ticket", 0.78),
                    _candidate("sop:change_flight", "change_flight", 0.73),
                ),
                allowed_actions=("START_SOP", "SUSPEND_AND_START", "CLARIFY"),
                thresholds={"classifierMinConfidence": 0.6},
            )
        )

        payload = captured_payloads[0]
        self.assertNotIn("enabledSopIds", payload["sessionState"])
        self.assertEqual(payload["sessionState"], {"activeTask": True, "activeTaskId": 9, "activeSopId": "flight_booking", "suspendedTaskCount": 0})
        self.assertLess(len(json.dumps(payload, ensure_ascii=False)), 1200)
        candidate = payload["candidates"][0]
        self.assertEqual(
            set(candidate),
            {
                "candidate_id",
                "candidate_type",
                "name",
                "score",
                "matched_terms",
                "requires_classifier",
                "reason",
            },
        )
        self.assertNotIn("score_breakdown", candidate)
        self.assertNotIn("risk_level", candidate)

    def test_llm_classifier_payload_remains_compact_for_full_finite_fallback_candidate_set(self) -> None:
        candidates = tuple(
            RouteCandidate(
                candidate_id=f"sop:test_{index}",
                candidate_type=CandidateType.SOP_INTENT,
                target_id=f"test_{index}",
                display_name=f"测试意图{index}",
                source="enabled_scope_fallback",
                score=0.45,
                score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=0.45),
                matched_terms=(),
                risk_level="MEDIUM",
                requires_classifier=True,
                reason="Enabled SOP finite candidate fallback after explicit and semantic recall returned empty",
            )
            for index in range(15)
        )
        payload = ClassifierInput(
            message="我想办个和机票有关的事情",
            session_state={"activeTask": False, "suspendedTaskCount": 0, "enabledSopIds": [str(index) for index in range(15)]},
            candidates=candidates,
            allowed_actions=("START_SOP", "CLARIFY"),
            thresholds={"classifierMinConfidence": 0.6},
        ).to_llm_payload()

        serialized = json.dumps(payload, ensure_ascii=False)

        self.assertLess(len(serialized), 3200)
        self.assertNotIn("Enabled SOP finite candidate fallback", serialized)
        self.assertNotIn("enabledSopIds", serialized)


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
