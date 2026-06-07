import unittest

from fastapi.testclient import TestClient

from app.main import app


class RuntimeLabSemanticEvidenceApiContractTest(unittest.TestCase):
    def test_message_response_includes_candidate_policy_and_classifier_evidence(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
            response = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "我想退费并开发票"},
            )

        self.assertEqual(response.status_code, 200)
        route_decision = response.json()["data"]["routeDecision"]
        self.assertEqual(route_decision["action"], "START_SOP")
        self.assertGreaterEqual(len(route_decision["candidates"]), 2)
        self.assertEqual(route_decision["policyGate"]["stage"], "post_classifier")
        self.assertEqual(route_decision["classifierRequest"]["allowedActions"][0], "CONTINUE_ACTIVE_SOP")
        self.assertEqual(route_decision["classifierResult"]["selected_action"], "START_SOP")
        self.assertEqual(route_decision["finalDecision"]["action"], "START_SOP")
