import unittest

from app.modules.customer_assistant.eval.promotion_report import (
    ChatflowDataReadiness,
    ShadowCandidateEvidence,
    build_promotion_report,
)
from app.modules.customer_assistant.eval.synthetic_cases import synthetic_cases


class CustomerAssistantPromotionReportTest(unittest.TestCase):
    def test_default_promotion_report_has_readiness_metrics_and_zero_live_calls(self) -> None:
        report = build_promotion_report(
            synthetic_cases(),
            chatflow_readiness=ChatflowDataReadiness(
                status="mock_fallback",
                strategy="explicit_fallback_mock",
                checked_sop_keys=["refund_ticket"],
            ),
            shadow_candidates=[
                ShadowCandidateEvidence(
                    case_id="synthetic-refund-ticket",
                    phase="task_recognition",
                    baseline={"commands": [{"taskKey": "refund_ticket"}]},
                    candidate={"commands": [{"taskKey": "refund_ticket"}]},
                    diff={"matches": True},
                )
            ],
        )

        data = report.to_dict()

        self.assertEqual(data["totalCases"], 20)
        self.assertEqual(data["liveModelCalls"], 0)
        self.assertEqual(data["taskRecognitionPassRate"], 1.0)
        self.assertEqual(data["recommendationPassRate"], 1.0)
        self.assertEqual(data["safetyPassRate"], 1.0)
        self.assertEqual(data["schemaFailureRate"], 0.0)
        self.assertGreaterEqual(data["eventCoveragePassRate"], 0.95)
        self.assertEqual(data["chatflowDataReadiness"]["status"], "mock_fallback")
        self.assertTrue(data["shadowCandidateDiffs"][0]["evidenceOnly"])
        self.assertNotIn("selectedRuntimeOutput", data["shadowCandidateDiffs"][0])


if __name__ == "__main__":
    unittest.main()
