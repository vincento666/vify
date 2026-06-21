import json
import unittest
from pathlib import Path

from app.modules.customer_assistant.domain.worker_profiles import (
    CustomerAssistantWorkerProfileCatalog,
    default_customer_assistant_worker_profiles_json,
)


class CustomerAssistantWorkerProfileCatalogTest(unittest.TestCase):
    def test_defaults_include_demo_worker_routing_metadata(self) -> None:
        catalog = CustomerAssistantWorkerProfileCatalog.default()
        profiles = catalog.list_profiles()

        self.assertGreaterEqual(len(profiles), 3)
        refund = catalog.resolve("refund_ticket")
        self.assertIsNotNone(refund)
        self.assertEqual(refund.worker_type, "chatflow_sop")
        self.assertEqual(refund.risk_policy_ref, "manual_confirm")

    def test_json_override_replaces_active_catalog(self) -> None:
        raw = json.dumps(
            {
                "profiles": [
                    {
                        "profileId": "configured_refund_stub",
                        "taskKey": "refund_ticket",
                        "taskType": "QA",
                        "workerType": "stub_qa",
                        "workerRef": "configured_refund_stub",
                        "modelPolicyRef": "demo-model",
                        "promptRef": "demo-prompt",
                        "toolRefs": ["lookup_order"],
                        "riskPolicyRef": "manual_confirm",
                    }
                ]
            }
        )

        catalog = CustomerAssistantWorkerProfileCatalog.from_json(raw)
        profiles = catalog.list_profiles()

        self.assertEqual(len(profiles), 1)
        self.assertEqual(catalog.resolve("refund_ticket").worker_ref, "configured_refund_stub")
        self.assertEqual(profiles[0]["toolRefs"], ["lookup_order"])

    def test_json_override_exposes_skill_policy_refs(self) -> None:
        raw = json.dumps(
            {
                "profiles": [
                    {
                        "profileId": "configured_refund_react",
                        "taskKey": "refund_ticket",
                        "taskType": "REFUND",
                        "workerType": "react_worker",
                        "workerRef": "configured_refund_react",
                        "modelPolicyRef": "demo-react-model",
                        "promptRef": "demo-react-prompt",
                        "toolRefs": ["lookup_order"],
                        "toolPolicyRef": "strict-read-before-write",
                        "riskPolicyRef": "manual_confirm_high_risk",
                        "outputSchemaRef": "refund_react_result_v2",
                    }
                ]
            }
        )

        profile = CustomerAssistantWorkerProfileCatalog.from_json(raw).resolve("refund_ticket")

        self.assertIsNotNone(profile)
        assert profile is not None
        self.assertEqual(profile.tool_policy_ref, "strict-read-before-write")
        self.assertEqual(profile.output_schema_ref, "refund_react_result_v2")

    def test_resolves_business_scoped_task_key_to_profile_family(self) -> None:
        profile = CustomerAssistantWorkerProfileCatalog.default().resolve("refund_ticket:MU5137-8899")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.profile_id, "refund_ticket_chatflow")

    def test_default_json_is_secret_free(self) -> None:
        raw = default_customer_assistant_worker_profiles_json()

        self.assertIn("refund_ticket", raw)
        self.assertNotIn("api_key", raw.lower())
        self.assertNotIn("token", raw.lower())

    def test_default_mvp_profiles_do_not_expose_legacy_stub_markers(self) -> None:
        raw = default_customer_assistant_worker_profiles_json()
        catalog = CustomerAssistantWorkerProfileCatalog.default()
        baggage = catalog.resolve("baggage_qa")

        self.assertIsNotNone(baggage)
        self.assertEqual(baggage.profile_id, "baggage_service_chatflow")
        self.assertEqual(baggage.worker_type, "chatflow_sop")
        self.assertEqual(baggage.worker_ref, "baggage_service")
        self.assertNotIn("stub_qa", raw)
        self.assertNotIn("baggage_allowance_stub", raw)
        self.assertNotIn("fake_stub_qa_model", raw)

    def test_repo_env_does_not_override_baggage_profile_to_legacy_stub(self) -> None:
        env_path = Path(__file__).resolve().parents[3] / ".env"
        self.assertTrue(env_path.exists())
        env_text = env_path.read_text(encoding="utf-8")
        profile_line = next(
            line
            for line in env_text.splitlines()
            if line.startswith("HIFY_CUSTOMER_ASSISTANT_WORKER_PROFILES_JSON=")
        )
        raw = profile_line.partition("=")[2]

        catalog = CustomerAssistantWorkerProfileCatalog.from_json(raw)
        baggage = catalog.resolve("baggage_qa")

        self.assertIsNotNone(baggage)
        self.assertEqual(baggage.worker_type, "chatflow_sop")
        self.assertEqual(baggage.worker_ref, "baggage_service")
        self.assertNotIn("baggage_allowance_stub", raw)
        self.assertNotIn("fake_stub_qa_model", raw)
