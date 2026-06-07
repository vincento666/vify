import unittest

from app.modules.runtime_lab.domain.candidates import (
    CandidateType,
    RouteCandidate,
    ScoreBreakdown,
    select_top_candidates,
)


class RouteCandidateTest(unittest.TestCase):
    def test_candidate_serializes_score_evidence(self) -> None:
        candidate = RouteCandidate(
            candidate_id="sop:refund_ticket",
            candidate_type=CandidateType.SOP_INTENT,
            target_id="refund_ticket",
            display_name="退票",
            source="mock_sop_manifest",
            score=1.0,
            score_breakdown=ScoreBreakdown(keyword=1.0, alias=0.0, semantic=0.0),
            matched_terms=("退票",),
            risk_level="LOW",
            requires_classifier=False,
            reason="exact strong keyword",
        )

        self.assertEqual(
            candidate.to_dict(),
            {
                "candidate_id": "sop:refund_ticket",
                "candidate_type": "SOP_INTENT",
                "target_id": "refund_ticket",
                "display_name": "退票",
                "source": "mock_sop_manifest",
                "score": 1.0,
                "score_breakdown": {"keyword": 1.0, "alias": 0.0, "semantic": 0.0},
                "matched_terms": ["退票"],
                "risk_level": "LOW",
                "requires_classifier": False,
                "reason": "exact strong keyword",
            },
        )

    def test_rejects_unknown_candidate_type(self) -> None:
        with self.assertRaises(ValueError):
            RouteCandidate(
                candidate_id="bad:1",
                candidate_type="FAQ_ANSWER",
                target_id="faq-1",
                display_name="FAQ",
                source="future",
                score=0.9,
                score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=0.9),
                matched_terms=(),
                risk_level="LOW",
                requires_classifier=True,
                reason="future type should be rejected in 030.1",
            )

    def test_top_k_orders_by_score_and_preserves_input_order_for_ties(self) -> None:
        candidates = [
            _candidate("sop:refund_ticket", 0.7),
            _candidate("sop:change_flight", 0.95),
            _candidate("sop:invoice_apply", 0.95),
            _candidate("clarify:no_match", 0.2, candidate_type=CandidateType.CLARIFY),
        ]

        top = select_top_candidates(candidates, top_k=3)

        self.assertEqual(
            [candidate.candidate_id for candidate in top],
            ["sop:change_flight", "sop:invoice_apply", "sop:refund_ticket"],
        )


def _candidate(
    candidate_id: str,
    score: float,
    candidate_type: CandidateType = CandidateType.SOP_INTENT,
) -> RouteCandidate:
    return RouteCandidate(
        candidate_id=candidate_id,
        candidate_type=candidate_type,
        target_id=candidate_id.split(":", 1)[1],
        display_name=candidate_id,
        source="test",
        score=score,
        score_breakdown=ScoreBreakdown(keyword=score, alias=0.0, semantic=0.0),
        matched_terms=(candidate_id,),
        risk_level="LOW",
        requires_classifier=score < 0.9,
        reason="test candidate",
    )
