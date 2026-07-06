import importlib
import importlib.util
import unittest

from app.modules.ai_assistant.domain.tools import ToolRegistry


def _load_adapter_module():
    module_name = "app.modules.ai_assistant.domain.business_adapter"
    if importlib.util.find_spec(module_name) is None:
        raise AssertionError("Business adapter module is missing: app.modules.ai_assistant.domain.business_adapter")
    return importlib.import_module(module_name)


class AiAssistantBusinessAdapterTest(unittest.TestCase):
    def test_mock_aviation_adapter_exposes_schema_risk_idempotency_compensation_and_audit_fields(self) -> None:
        adapter_module = _load_adapter_module()
        adapter = adapter_module.MockAviationAdapter()

        schemas = {schema.name: schema for schema in adapter.list_tool_schemas()}

        self.assertEqual(
            set(schemas),
            {
                "mock_aviation.refund",
                "mock_aviation.change_ticket",
                "mock_aviation.baggage",
                "mock_aviation.flight_disruption",
            },
        )
        for schema in schemas.values():
            self.assertEqual(schema.adapter_name, "mock_aviation")
            self.assertIn(schema.risk_level, {"READ", "BUSINESS_WRITE"})
            self.assertEqual(schema.input_schema["type"], "object")
            self.assertEqual(schema.output_schema["type"], "object")
            self.assertGreater(len(schema.idempotency_fields), 0)
            self.assertIn("adapterName", schema.audit_fields)
            self.assertIn("mockOnly", schema.audit_fields)
            self.assertIsNotNone(schema.compensation)

    def test_mock_aviation_adapter_invocation_returns_idempotency_compensation_and_audit_without_real_rules(self) -> None:
        adapter_module = _load_adapter_module()
        adapter = adapter_module.MockAviationAdapter()

        result = adapter.invoke(
            "mock_aviation.refund",
            {"caseId": "case-refund-1", "passengerId": "PAX-1", "request": "refund request"},
        )

        self.assertEqual(result.status, "MOCK_ACCEPTED")
        self.assertEqual(result.idempotency_key, "mock_aviation.refund:case-refund-1")
        self.assertEqual(result.audit["adapterName"], "mock_aviation")
        self.assertEqual(result.audit["scenario"], "refund")
        self.assertTrue(result.audit["mockOnly"])
        self.assertFalse(result.audit["realAviationRulesApplied"])
        self.assertEqual(result.compensation_transaction["status"], "MOCK_COMPENSATION_READY")
        self.assertEqual(result.output["businessEffect"], "mock_only")

    def test_builtin_tool_registry_exposes_mock_aviation_adapter_for_live_uat(self) -> None:
        manifests = {manifest.name: manifest for manifest in ToolRegistry.with_builtin_tools().list_manifests()}

        for tool_name in {
            "mock_aviation.refund",
            "mock_aviation.change_ticket",
            "mock_aviation.baggage",
            "mock_aviation.flight_disruption",
        }:
            self.assertIn(tool_name, manifests)
            self.assertEqual(manifests[tool_name].policy_ref.split(":")[0], "business_adapter")


if __name__ == "__main__":
    unittest.main()
