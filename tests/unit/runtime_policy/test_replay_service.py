import unittest
from copy import deepcopy
from datetime import datetime

from app.modules.runtime_policy.domain.governance import RuntimePolicyReplayService
from tests.contract.test_runtime_policy_profile_api import _profile_payload


class RuntimePolicyReplayServiceTest(unittest.TestCase):
    def test_golden_matrix_replay_returns_expected_vs_actual_results(self) -> None:
        row = _profile_row("042.2 golden", profile_id=9)

        result = RuntimePolicyReplayService().replay_golden_matrix(row)

        self.assertEqual(result["runType"], "golden_matrix")
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["result"]["caseCount"], 4)
        self.assertEqual(result["result"]["failedCount"], 0)
        self.assertTrue(result["result"]["cases"][0]["expected"])
        self.assertTrue(result["result"]["cases"][0]["actual"])
        self.assertEqual(result["riskDeltas"]["unsupportedActionCount"], 0)

    def test_decision_log_replay_reports_changed_decisions_and_risk_deltas(self) -> None:
        row = _profile_row("042.2 logs", profile_id=10)
        logs = [
            {
                "id": 31,
                "session_id": 99,
                "user_message": "机场附近打印店在哪里",
                "final_action": "AGENT_FALLBACK",
                "source_layer": "agent_policy",
                "reason_code": "AGENT_ANSWER",
                "mutates_sop_state": False,
                "handoff_triggered": False,
            }
        ]

        result = RuntimePolicyReplayService().replay_decision_logs(row, logs)

        self.assertEqual(result["runType"], "decision_log_replay")
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["passed"])
        self.assertEqual(result["result"]["logCount"], 1)
        self.assertEqual(result["result"]["changedDecisionCount"], 0)
        self.assertEqual(result["riskDeltas"]["handoffRateDelta"], 0.0)
        self.assertEqual(result["riskDeltas"]["clarificationRateDelta"], 0.0)
        self.assertEqual(result["riskDeltas"]["unsupportedActionCount"], 0)


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
