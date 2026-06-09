import unittest
from copy import deepcopy
from datetime import datetime

from app.modules.runtime_policy.domain.governance import RuntimePolicyValidationService
from tests.contract.test_runtime_policy_profile_api import _profile_payload


class RuntimePolicyValidationServiceTest(unittest.TestCase):
    def test_validation_rejects_malformed_profile_row(self) -> None:
        row = _profile_row("malformed", profile_id=7)
        row["thresholds"]["strongAcceptThreshold"] = 1.2
        row["classifier"]["mode"] = "llm"
        row["classifier"]["model"] = ""
        row["fallback_agent"]["allowedResponseTypes"] = ["answer", "teleport"]

        result = RuntimePolicyValidationService().validate_profile_row(row)

        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["passed"])
        self.assertIn("thresholds.strongAcceptThreshold.out_of_range", result["failureReasons"])
        self.assertIn("classifier.model.required", result["failureReasons"])
        self.assertIn("fallbackAgent.allowedResponseTypes.unsupported", result["failureReasons"])

    def test_validation_passes_valid_profile_row_with_guardrail_defaults(self) -> None:
        row = _profile_row("valid", profile_id=8)

        result = RuntimePolicyValidationService().validate_profile_row(row)

        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["passed"])
        self.assertEqual(result["failureReasons"], [])
        self.assertEqual(result["guardrails"]["maxHandoffRateDelta"], 0.1)
        self.assertEqual(result["guardrails"]["maxClarificationRateDelta"], 0.15)
        self.assertEqual(result["guardrails"]["maxUnsupportedActionCount"], 0)
        self.assertTrue(result["guardrails"]["requireGoldenMatrixPass"])
        self.assertTrue(result["guardrails"]["requireReplayReport"])


def _profile_row(name: str, *, profile_id: int) -> dict[str, object]:
    payload = deepcopy(_profile_payload(name))
    now = datetime.now()
    return {
        "id": profile_id,
        "name": payload["name"],
        "description": payload["description"],
        "status": payload["status"],
        "version": 1,
        "mode": payload["mode"],
        "bindings": payload["bindings"],
        "thresholds": payload["thresholds"],
        "classifier": payload["classifier"],
        "faq": payload["faq"],
        "rag": payload["rag"],
        "fallback_agent": payload["fallbackAgent"],
        "handoff": payload["handoff"],
        "audit": payload["audit"],
        "deleted": False,
        "created_at": now,
        "updated_at": now,
    }


if __name__ == "__main__":
    unittest.main()
