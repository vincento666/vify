import unittest

from app.modules.customer_assistant.eval.exporter import export_candidate_cases_from_events, redact_case
from app.modules.customer_assistant.eval.fixtures import golden_cases
from app.modules.customer_assistant.eval.runner import run_customer_assistant_eval
from app.modules.customer_assistant.eval.schemas import CustomerAssistantEvalCase


class CustomerAssistantEvalDataTest(unittest.TestCase):
    def test_exports_shadow_and_timing_events_into_redacted_candidate_cases(self) -> None:
        events = [
            {
                "type": "llm_shadow_diff_recorded",
                "payload": {
                    "phase": "task_recognition",
                    "actor": "customer",
                    "baseline": {"commands": [{"taskKey": "refund_ticket", "businessKey": "TK-100"}]},
                    "shadow": {"commands": [{"taskKey": "refund_ticket", "businessKey": "TK-100"}]},
                    "diff": {"matches": True},
                },
            },
            {
                "type": "recommendation_completed",
                "payload": {"elapsedMs": 12, "customerPhone": "13800138000"},
            },
        ]

        cases = export_candidate_cases_from_events(events)
        redacted = redact_case(cases[0])

        self.assertIsInstance(cases[0], CustomerAssistantEvalCase)
        self.assertEqual(cases[0].task_recognition.expected_task_key, "refund_ticket")
        self.assertEqual(cases[0].timing.run_elapsed_ms, 12)
        self.assertNotIn("13800138000", str(redacted))

    def test_golden_cases_run_deterministic_report_without_live_llm(self) -> None:
        report = run_customer_assistant_eval(golden_cases())

        self.assertGreaterEqual(report.total_cases, 5)
        self.assertIn("taskRecognition", report.sections)
        self.assertIn("recommendation", report.sections)
        self.assertIn("safety", report.sections)
        self.assertEqual(report.live_model_calls, 0)


if __name__ == "__main__":
    unittest.main()
