import unittest

from app.modules.runtime_lab.domain.candidates import CandidateType
from app.modules.runtime_lab.domain.explicit_signals import ExplicitSignalDetector
from app.modules.runtime_lab.domain.sop import mock_sop_manifests


class ExplicitHandoffSignalTest(unittest.TestCase):
    def test_human_support_phrase_recalls_handoff_candidate(self) -> None:
        candidates = _detect("我要人工客服")

        self.assertEqual(candidates[0].candidate_type, CandidateType.HANDOFF_TO_HUMAN)
        self.assertEqual(candidates[0].target_id, "USER_REQUEST")
        self.assertEqual(candidates[0].matched_terms, ("人工客服",))
        self.assertFalse(candidates[0].requires_classifier)

    def test_complaint_compliance_safety_and_unsupported_phrases_recall_handoff(self) -> None:
        examples = (
            ("我要投诉你们", "COMPLAINT", "投诉"),
            ("我要找民航局监管", "COMPLIANCE", "民航局"),
            ("我要报警处理这个安全事故", "SAFETY", "报警"),
            ("这个机器人处理不了", "UNSUPPORTED", "这个机器人处理不了"),
        )

        for message, reason_code, matched_term in examples:
            with self.subTest(message=message):
                candidates = _detect(message)

                self.assertEqual(candidates[0].candidate_type, CandidateType.HANDOFF_TO_HUMAN)
                self.assertEqual(candidates[0].target_id, reason_code)
                self.assertIn(matched_term, candidates[0].matched_terms)
                self.assertEqual(candidates[0].source, "explicit_signal")


def _detect(message: str):
    detector = ExplicitSignalDetector(mock_sop_manifests())
    return detector.detect(message, active_task=None, suspended_tasks=())
