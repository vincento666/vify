import unittest

from app.modules.runtime_lab.domain.candidates import CandidateType
from app.modules.runtime_lab.domain.recall import MockSemanticCandidateRecall
from app.modules.runtime_lab.domain.sop import mock_sop_manifests


class MockSemanticCandidateRecallTest(unittest.TestCase):
    def test_recalls_mock_sop_candidate_from_semantic_fixture(self) -> None:
        candidates = MockSemanticCandidateRecall(mock_sop_manifests()).recall(
            "我需要报销凭证",
            active_task=None,
            suspended_tasks=(),
        )

        self.assertEqual(candidates[0].candidate_type, CandidateType.SOP_INTENT)
        self.assertEqual(candidates[0].target_id, "invoice_apply")
        self.assertGreaterEqual(candidates[0].score, 0.7)
        self.assertLess(candidates[0].score, 0.9)
        self.assertEqual(candidates[0].score_breakdown.semantic, candidates[0].score)
        self.assertTrue(candidates[0].requires_classifier)

    def test_recalls_suspended_task_from_resume_summary(self) -> None:
        candidates = MockSemanticCandidateRecall(mock_sop_manifests()).recall(
            "继续处理退票",
            active_task=None,
            suspended_tasks=({"id": 7, "sop_id": "refund_ticket", "resume_summary": "退票已收集订单号"},),
        )

        self.assertEqual(candidates[0].candidate_type, CandidateType.SUSPENDED_TASK_RESUME)
        self.assertEqual(candidates[0].target_id, "7")
        self.assertIn("退票", candidates[0].matched_terms)
        self.assertEqual(candidates[0].score_breakdown.semantic, candidates[0].score)

    def test_active_task_continuation_candidate_is_included_with_active_context(self) -> None:
        candidates = MockSemanticCandidateRecall(mock_sop_manifests()).recall(
            "这是订单号 TK-100",
            active_task={"id": 3, "sop_id": "refund_ticket", "current_step": "collect_order_no"},
            suspended_tasks=(),
        )

        self.assertEqual(candidates[0].candidate_type, CandidateType.ACTIVE_TASK_CONTINUE)
        self.assertEqual(candidates[0].target_id, "3")
        self.assertEqual(candidates[0].score_breakdown.semantic, 0.55)

    def test_conflicting_semantic_candidates_keep_evidence_for_later_arbitration(self) -> None:
        candidates = MockSemanticCandidateRecall(mock_sop_manifests()).recall(
            "我想退费并开发票",
            active_task=None,
            suspended_tasks=(),
        )

        self.assertEqual(
            [candidate.target_id for candidate in candidates[:2]],
            ["refund_ticket", "invoice_apply"],
        )
        self.assertTrue(all(candidate.requires_classifier for candidate in candidates[:2]))
        self.assertTrue(all(candidate.score_breakdown.semantic > 0 for candidate in candidates[:2]))
