import unittest

from fastapi.testclient import TestClient

from app.main import app


class RuntimeLabSemanticApiE2ETest(unittest.TestCase):
    def test_semantic_route_scenarios_return_candidate_evidence(self) -> None:
        with TestClient(app) as client:
            alias_session = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
            alias_start = _message(client, alias_session, "我想退机票")

            conflict_session = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
            ambiguous = _message(client, conflict_session, "我想退费并开发票")

            active_session = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
            _message(client, active_session, "我要退票")
            active_switch = _message(client, active_session, "我需要报销凭证")

            reject_session = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
            _message(client, reject_session, "我要退票")
            _message(client, reject_session, "TK-100")
            rejected = _message(client, reject_session, "我需要报销凭证")

            resume_session = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
            _message(client, resume_session, "我要退票")
            _message(client, resume_session, "我要开发票")
            _message(client, resume_session, "INV-200")
            _message(client, resume_session, "确认")
            resumed = _message(client, resume_session, "继续处理退票")

        self.assertEqual(alias_start["routeDecision"]["action"], "START_SOP")
        self.assertEqual(alias_start["activeTask"]["sopId"], "refund_ticket")
        self.assertEqual(ambiguous["routeDecision"]["policyGate"]["stage"], "post_classifier")
        self.assertGreaterEqual(len(ambiguous["routeDecision"]["candidates"]), 2)
        self.assertEqual(active_switch["routeDecision"]["action"], "SUSPEND_AND_START")
        self.assertEqual(active_switch["activeTask"]["sopId"], "invoice_apply")
        self.assertEqual(rejected["routeDecision"]["action"], "REJECT_SWITCH_CONTINUE_ACTIVE")
        self.assertEqual(resumed["routeDecision"]["action"], "RESUME_TASK")
        self.assertEqual(resumed["activeTask"]["sopId"], "refund_ticket")


def _message(client: TestClient, session_id: int, message: str) -> dict:
    response = client.post(
        f"/api/v1/runtime-lab/sessions/{session_id}/messages",
        json={"message": message},
    )
    assert response.status_code == 200
    return response.json()["data"]
