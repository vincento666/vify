import unittest
from unittest.mock import MagicMock, patch

from app.modules.runtime_lab.domain import candidates
from app.modules.runtime_lab.domain.classifier import ClassifierInput, ClassifierResult
from app.modules.runtime_lab.domain.faq_gate import FaqAnswerEvidence, FaqAnswerProposal
from app.modules.runtime_lab.domain.router import RouteDecision
from app.modules.runtime_lab.domain.service import RuntimeLabService


class CandidateFusionTest(unittest.TestCase):
    def test_fuses_duplicate_canonical_candidate_with_weighted_provenance(self) -> None:
        fused = candidates.fuse_candidates(
            [
                _candidate(
                    "sop:refund_ticket",
                    0.9,
                    source="explicit_signal",
                    matched_terms=("退票",),
                    risk_level="LOW",
                    requires_classifier=False,
                ),
                _candidate(
                    "sop:refund_ticket",
                    0.8,
                    source="mock_semantic_recall",
                    matched_terms=("手续费", "退票"),
                    risk_level="HIGH",
                    requires_classifier=True,
                ),
            ],
            source_weights={"explicit_signal": 0.5},
        )

        self.assertEqual(len(fused), 1)
        candidate = fused[0]
        self.assertEqual(candidate.candidate_id, "sop:refund_ticket")
        self.assertEqual(candidate.score, 0.8)
        self.assertEqual(candidate.matched_terms, ("退票", "手续费"))
        self.assertEqual(candidate.risk_level, "HIGH")
        self.assertTrue(candidate.requires_classifier)
        self.assertEqual(
            candidate.to_dict()["sourceEvidence"],
            [
                {
                    "candidateId": "sop:refund_ticket",
                    "candidateKey": "SOP_INTENT:refund_ticket",
                    "source": "explicit_signal",
                    "rawScore": 0.9,
                    "sourceWeight": 0.5,
                    "weightedScore": 0.45,
                },
                {
                    "candidateId": "sop:refund_ticket",
                    "candidateKey": "SOP_INTENT:refund_ticket",
                    "source": "mock_semantic_recall",
                    "rawScore": 0.8,
                    "sourceWeight": 1.0,
                    "weightedScore": 0.8,
                },
            ],
        )

    def test_top_k_capacity_and_ties_are_computed_after_canonical_fusion(self) -> None:
        fused = candidates.fuse_candidates(
            [
                _candidate("sop:refund_ticket", 0.96, source="explicit_signal"),
                _candidate("sop:refund_ticket", 0.95, source="mock_semantic_recall"),
                _candidate("sop:change_flight", 0.94, source="mock_semantic_recall"),
            ],
            source_weights={},
        )

        self.assertEqual(
            [candidate.candidate_id for candidate in candidates.select_top_candidates(fused, top_k=2)],
            ["sop:refund_ticket", "sop:change_flight"],
        )
        tied = candidates.select_top_candidates(
            [
                _candidate("sop:refund_ticket", 0.8, source="mock_semantic_recall"),
                _candidate("sop:change_flight", 0.8, source="mock_semantic_recall"),
            ],
            top_k=2,
        )
        self.assertEqual(
            [candidate.candidate_id for candidate in tied],
            ["sop:change_flight", "sop:refund_ticket"],
        )

    def test_same_faq_from_exact_and_semantic_lanes_fuses_by_faq_target(self) -> None:
        service = RuntimeLabService(
            MagicMock(),
            faq_answer_gate=_StaticFaqGate(_faq_proposal()),
            faq_semantic_gate=_StaticFaqSemanticGate(_semantic_faq_decision()),
        )

        fused = [
            candidate
            for candidate in service._route_candidates("儿童票可以退吗？", None, [], None)
            if candidate.candidate_type == candidates.CandidateType.ANSWER_FAQ
        ]

        self.assertEqual(len(fused), 1)
        self.assertEqual(fused[0].canonical_key, "ANSWER_FAQ:faq:12")
        self.assertEqual(fused[0].candidate_id, "faq:12")
        self.assertEqual(
            [observation["source"] for observation in fused[0].source_evidence],
            ["faq_exact", "faq_semantic"],
        )

    def test_semantic_faq_keeps_legacy_target_id_with_internal_canonical_identity(self) -> None:
        service = RuntimeLabService(
            MagicMock(),
            faq_semantic_gate=_StaticFaqSemanticGate(_semantic_faq_decision()),
        )

        semantic = service._faq_semantic_candidates(
            "儿童票可以退吗？",
            active_task=None,
            suspended_tasks=[],
        )[0]

        self.assertEqual(semantic.target_id, "faq_semantic:faq:12")
        self.assertEqual(semantic.canonical_key, "ANSWER_FAQ:faq:12")
        self.assertEqual(semantic.to_dict()["target_id"], "faq_semantic:faq:12")
        self.assertNotIn("canonicalTargetId", semantic.to_dict())

    def test_fake_arbitration_uses_source_evidence_for_a_clamped_canonical_tie(self) -> None:
        service = RuntimeLabService(MagicMock())
        irregular = _candidate("sop:irregular_flight", 1.1, source="explicit_signal")
        refund = _candidate("sop:refund_ticket", 1.2, source="explicit_signal")

        with (
            patch.object(service._explicit_signals, "detect", return_value=[irregular, refund]),
            patch.object(service._semantic_recall, "recall", return_value=[]),
        ):
            decision = service.preview_route("我要退票，顺便确认一下非自愿政策")

        self.assertEqual(
            [candidate["candidate_id"] for candidate in decision.candidates],
            ["sop:irregular_flight", "sop:refund_ticket"],
        )
        self.assertEqual(decision.target_sop_id, "refund_ticket")

    def test_conflicting_duplicate_payload_fails_closed_before_classifier(self) -> None:
        classifier = _RecordingClassifier()
        service = RuntimeLabService(MagicMock(), classifier=classifier)
        explicit = _candidate(
            "sop:refund_ticket",
            0.9,
            source="explicit_signal",
            payload={"binding": "left"},
        )
        semantic = _candidate(
            "sop:refund_ticket",
            0.8,
            source="mock_semantic_recall",
            payload={"binding": "right"},
        )

        with (
            patch.object(service._explicit_signals, "detect", return_value=[explicit]),
            patch.object(service._semantic_recall, "recall", return_value=[semantic]),
        ):
            decision = service.preview_route("我要退票")

        self.assertEqual(decision.action, "CLARIFY")
        self.assertEqual(decision.policy_gate["stage"], "candidate_fusion_conflict")
        self.assertEqual(classifier.inputs, [])
        self.assertEqual(decision.candidates[0]["payload"]["candidateFusion"]["outcome"], "CONFLICT")


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
            rationale="test classifier would mutate if fusion did not fail closed",
            needs_clarification=False,
            clarification_question=None,
        )


class _StaticFaqGate:
    def __init__(self, proposal: FaqAnswerProposal) -> None:
        self._proposal = proposal

    def propose(
        self,
        message: str,
        *,
        active_task: dict | None,
        suspended_tasks: list[dict],
    ) -> FaqAnswerProposal | None:
        del active_task, suspended_tasks
        return self._proposal if "儿童票" in message else None


class _StaticFaqSemanticGate:
    def __init__(self, decision: RouteDecision) -> None:
        self._decision = decision

    def decide(
        self,
        message: str,
        *,
        active_task: dict | None,
        suspended_tasks: list[dict],
    ) -> RouteDecision | None:
        del active_task, suspended_tasks
        return self._decision if "儿童票" in message else None


def _faq_proposal() -> FaqAnswerProposal:
    return FaqAnswerProposal(
        answer="儿童票如未使用可按客票规则申请退票。",
        confidence=0.95,
        margin=0.50,
        evidence=FaqAnswerEvidence(
            faq_id=12,
            question="儿童票可以退吗？",
            answer="儿童票如未使用可按客票规则申请退票。",
            score=2.0,
            match_type="EXACT",
            source="structured_faq",
            matched_terms=("儿童票",),
        ),
    )


def _semantic_faq_decision() -> RouteDecision:
    return RouteDecision(
        action="ANSWER_FAQ",
        reason="Semantic FAQ accepted before SOP arbitration",
        faq_answer={
            "sourceLayer": "faq_semantic",
            "reasonCode": "SEMANTIC_HIGH_CONFIDENCE",
            "answer": "儿童票如未使用可按客票规则申请退票。",
            "confidence": 0.91,
            "margin": 0.31,
            "mutatesSopState": False,
            "evidence": {
                "faqId": 12,
                "question": "儿童票可以退吗？",
                "answer": "儿童票如未使用可按客票规则申请退票。",
                "score": 0.91,
                "matchType": "VECTOR",
                "source": "semantic_faq",
                "matchedTerms": ["退票"],
            },
        },
    )


def _candidate(
    candidate_id: str,
    score: float,
    *,
    source: str,
    matched_terms: tuple[str, ...] = (),
    risk_level: str = "LOW",
    requires_classifier: bool = True,
    payload: dict[str, str] | None = None,
) -> candidates.RouteCandidate:
    return candidates.RouteCandidate(
        candidate_id=candidate_id,
        candidate_type=candidates.CandidateType.SOP_INTENT,
        target_id=candidate_id.split(":", 1)[1],
        display_name=candidate_id,
        source=source,
        score=score,
        score_breakdown=candidates.ScoreBreakdown(keyword=score, alias=0.0, semantic=0.0),
        matched_terms=matched_terms,
        risk_level=risk_level,
        requires_classifier=requires_classifier,
        reason="candidate fusion fixture",
        payload=payload,
    )
