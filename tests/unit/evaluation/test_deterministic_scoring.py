import unittest

from app.modules.evaluation.domain.scoring import evaluate_sample


class DeterministicScoringTest(unittest.TestCase):
    def test_exact_match_can_ignore_case_and_whitespace(self) -> None:
        result = evaluate_sample(
            evaluator_type="EXACT_MATCH",
            config={"ignoreCase": True},
            expected_output="Refund approved",
            actual_output=" refund approved ",
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)

    def test_contains_keywords_reports_missing_terms(self) -> None:
        result = evaluate_sample(
            evaluator_type="CONTAINS_KEYWORDS",
            config={"keywords": ["refund", "policy"], "matchMode": "all", "ignoreCase": True},
            expected_output="",
            actual_output="The refund is available within seven days.",
        )

        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.5)
        self.assertIn("policy", result.reason)


if __name__ == "__main__":
    unittest.main()
