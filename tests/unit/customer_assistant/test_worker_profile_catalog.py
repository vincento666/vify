import json
import unittest

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

    def test_resolves_business_scoped_task_key_to_profile_family(self) -> None:
        profile = CustomerAssistantWorkerProfileCatalog.default().resolve("refund_ticket:MU5137-8899")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.profile_id, "refund_ticket_chatflow")

    def test_default_json_is_secret_free(self) -> None:
        raw = default_customer_assistant_worker_profiles_json()

        self.assertIn("refund_ticket", raw)
        self.assertNotIn("api_key", raw.lower())
        self.assertNotIn("token", raw.lower())
