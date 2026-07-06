import importlib
import importlib.util
import unittest


def _load_adapter_module():
    module_name = "app.modules.ai_assistant.domain.business_adapter"
    if importlib.util.find_spec(module_name) is None:
        raise AssertionError("Business adapter module is missing: app.modules.ai_assistant.domain.business_adapter")
    return importlib.import_module(module_name)


class AiAssistantMockAviationAdapterEvalTest(unittest.TestCase):
    def test_mock_aviation_eval_cases_cover_allowed_scenarios_without_real_rules(self) -> None:
        adapter_module = _load_adapter_module()
        adapter = adapter_module.MockAviationAdapter()
        cases = adapter_module.mock_aviation_eval_cases()

        self.assertEqual([case["scenario"] for case in cases], ["refund", "change_ticket", "baggage", "flight_disruption"])
        for case in cases:
            result = adapter.invoke(case["toolName"], case["input"])
            self.assertEqual(result.status, "MOCK_ACCEPTED")
            self.assertEqual(result.audit["scenario"], case["scenario"])
            self.assertTrue(result.audit["mockOnly"])
            self.assertFalse(result.audit["realAviationRulesApplied"])
            self.assertIn("businessEffect", result.output)


if __name__ == "__main__":
    unittest.main()
