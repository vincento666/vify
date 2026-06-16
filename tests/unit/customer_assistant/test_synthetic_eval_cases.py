import unittest

from app.modules.customer_assistant.eval.synthetic_cases import synthetic_cases


class CustomerAssistantSyntheticEvalCasesTest(unittest.TestCase):
    def test_synthetic_cases_cover_promotion_readiness_matrix(self) -> None:
        cases = synthetic_cases()
        categories = {case.category for case in cases}
        event_types = {
            event_type
            for case in cases
            for event_type in case.metadata.get("expected_event_types", [])
        }
        action_states = {
            state
            for case in cases
            for state in case.metadata.get("expected_action_states", [])
        }

        self.assertGreaterEqual(len(cases), 20)
        self.assertLessEqual(len(cases), 40)
        self.assertTrue(
            {
                "refund",
                "baggage",
                "combined",
                "ambiguous",
                "cancellation",
                "operator",
                "system",
                "high_risk_action",
                "worker_failure",
                "harness_sub_agent",
            }.issubset(categories)
        )
        self.assertIn("refund_ticket", {case.task_recognition.expected_task_key for case in cases})
        self.assertIn("baggage_allowance", {case.task_recognition.expected_task_key for case in cases})
        self.assertIn("proposed_action_created", event_types)
        self.assertIn("worker_failed", event_types)
        self.assertIn("PROPOSED", action_states)
        self.assertFalse(
            any(case.safety.high_risk_action_executed_without_confirmation for case in cases)
        )


if __name__ == "__main__":
    unittest.main()
