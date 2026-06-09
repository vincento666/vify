import unittest

from app.modules.runtime_lab.domain.candidates import CandidateType
from app.modules.runtime_lab.domain.explicit_signals import ExplicitSignalDetector
from app.modules.runtime_lab.domain.sop import mock_sop_manifests


class ExplicitSignalDetectorTest(unittest.TestCase):
    def test_strong_keyword_candidate_can_start_without_classifier_when_no_active_task(self) -> None:
        candidates = ExplicitSignalDetector(mock_sop_manifests()).detect(
            "我要退票",
            active_task=None,
            suspended_tasks=(),
        )

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate.candidate_type, CandidateType.SOP_INTENT)
        self.assertEqual(candidate.target_id, "refund_ticket")
        self.assertEqual(candidate.score, 1.2)
        self.assertEqual(candidate.score_breakdown.keyword, 1.2)
        self.assertFalse(candidate.requires_classifier)

    def test_transactional_action_beats_background_irregular_flight_signal(self) -> None:
        candidates = ExplicitSignalDetector(mock_sop_manifests()).detect(
            "航班延误了，帮我改签到明天上午",
            active_task=None,
            suspended_tasks=(),
        )

        self.assertGreaterEqual(len(candidates), 2)
        self.assertEqual(candidates[0].target_id, "change_flight")
        self.assertGreater(candidates[0].score, candidates[1].score)

    def test_strong_trigger_template_can_require_multiple_terms_without_literal_keyword(self) -> None:
        manifests = mock_sop_manifests()
        refund_manifest = manifests["refund_ticket"]

        candidates = ExplicitSignalDetector(manifests).detect(
            "我不确定今天还能不能飞，这张票款想拿回来，先帮我处理一下",
            active_task=None,
            suspended_tasks=(),
        )

        self.assertGreaterEqual(len(refund_manifest.strong_trigger_templates), 3)
        self.assertEqual(candidates[0].target_id, "refund_ticket")
        self.assertEqual(candidates[0].score, 1.0)
        self.assertEqual(candidates[0].score_breakdown.keyword, 1.0)
        self.assertIn("票款", candidates[0].matched_terms)
        self.assertIn("拿回来", candidates[0].matched_terms)
        self.assertIn("template", candidates[0].reason.lower())

    def test_route_flight_booking_utterance_is_not_forced_into_strong_trigger(self) -> None:
        candidates = ExplicitSignalDetector(mock_sop_manifests()).detect(
            "我要订广州飞北京的航班",
            active_task=None,
            suspended_tasks=(),
        )

        self.assertEqual(candidates, [])

    def test_colloquial_handoff_phrases_win_as_explicit_handoff_candidates(self) -> None:
        detector = ExplicitSignalDetector(mock_sop_manifests())

        for message in ("别机器人了帮我接人工", "麻烦转接客服人员", "这个退款争议很复杂你们机器人无法处理"):
            with self.subTest(message=message):
                candidates = detector.detect(message, active_task=None, suspended_tasks=())

                self.assertEqual(candidates[0].candidate_type, CandidateType.HANDOFF_TO_HUMAN)
                self.assertEqual(candidates[0].source, "explicit_signal")

    def test_airport_facility_questions_do_not_create_sop_candidates(self) -> None:
        detector = ExplicitSignalDetector(mock_sop_manifests())

        for message in ("机场附近能寄存行李吗", "值机柜台旁边有打印店吗"):
            with self.subTest(message=message):
                candidates = detector.detect(message, active_task=None, suspended_tasks=())

                self.assertEqual(candidates, [])

    def test_alias_keyword_candidate_keeps_score_evidence_and_requires_later_arbitration(self) -> None:
        candidates = ExplicitSignalDetector(mock_sop_manifests()).detect(
            "我想退机票",
            active_task=None,
            suspended_tasks=(),
        )

        self.assertEqual(candidates[0].target_id, "refund_ticket")
        self.assertEqual(candidates[0].score, 0.85)
        self.assertEqual(candidates[0].score_breakdown.alias, 0.85)
        self.assertTrue(candidates[0].requires_classifier)

    def test_resume_phrase_and_ordinal_reference_target_single_suspended_task(self) -> None:
        suspended = ({"id": 7, "sop_id": "refund_ticket", "resume_summary": "退票已暂停"},)
        detector = ExplicitSignalDetector(mock_sop_manifests())

        phrase = detector.detect("继续", active_task=None, suspended_tasks=suspended)
        ordinal = detector.detect("继续第一个", active_task=None, suspended_tasks=suspended)
        described = detector.detect("继续刚才的退票", active_task=None, suspended_tasks=suspended)

        self.assertEqual(phrase[0].candidate_type, CandidateType.SUSPENDED_TASK_RESUME)
        self.assertEqual(phrase[0].target_id, "7")
        self.assertEqual(phrase[0].score, 0.9)
        self.assertEqual(ordinal[0].target_id, "7")
        self.assertEqual(ordinal[0].matched_terms, ("继续第一个",))
        self.assertEqual(described[0].target_id, "7")

    def test_refusal_creates_clarify_candidate_and_detector_does_not_fill_business_slots(self) -> None:
        candidates = ExplicitSignalDetector(mock_sop_manifests()).detect(
            "不用了 TK-100",
            active_task={"id": 1, "sop_id": "refund_ticket", "current_step": "collect_order_no"},
            suspended_tasks=(),
        )

        self.assertEqual(candidates[0].candidate_type, CandidateType.CLARIFY)
        self.assertEqual(candidates[0].target_id, "clarify:no_op")
        self.assertNotIn("order_no", candidates[0].to_dict())
        self.assertNotIn("TK-100", candidates[0].reason)
