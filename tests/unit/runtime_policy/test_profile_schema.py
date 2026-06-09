import unittest

from pydantic import ValidationError

from app.modules.runtime_policy.web.schemas import RuntimePolicyProfileRequest
from tests.contract.test_runtime_policy_profile_api import _profile_payload


class RuntimePolicyProfileSchemaTest(unittest.TestCase):
    def test_thresholds_are_bounded_and_live_adapters_require_safe_refs(self) -> None:
        payload = _profile_payload(name="unit schema")
        payload["thresholds"] = {
            **payload["thresholds"],
            "ragMinScore": 1.2,
        }

        with self.assertRaises(ValidationError):
            RuntimePolicyProfileRequest.model_validate(payload)

        weighted_payload = _profile_payload(name="unit candidate weights")
        weighted_payload["thresholds"] = {
            **weighted_payload["thresholds"],
            "candidateSourceWeights": {"": 1.0, "ANSWER_FAQ": 6.0},
        }

        with self.assertRaises(ValidationError):
            RuntimePolicyProfileRequest.model_validate(weighted_payload)

        live_payload = _profile_payload(name="unit live schema")
        live_payload["classifier"] = {
            **live_payload["classifier"],
            "mode": "llm",
            "baseUrl": "https://llm.example.test/v1",
            "apiKeyRef": "secret/runtime/classifier",
            "model": "prod-classifier",
        }
        live_payload["fallbackAgent"] = {
            **live_payload["fallbackAgent"],
            "type": "existing_agent",
            "agentId": 42,
        }

        request = RuntimePolicyProfileRequest.model_validate(live_payload)

        self.assertEqual(request.classifier.mode, "llm")
        self.assertEqual(request.fallback_agent.agent_id, 42)


if __name__ == "__main__":
    unittest.main()
