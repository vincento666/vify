import unittest
from copy import deepcopy
from datetime import datetime
from typing import Any

from app.modules.runtime_policy.domain.governance import RuntimePolicyReplayService
from tests.contract.test_runtime_policy_profile_api import _profile_payload


class RuntimePolicyReplayServiceTest(unittest.TestCase):
    def test_golden_matrix_replay_returns_expected_vs_actual_results(self) -> None:
        row = _profile_row("042.2 golden", profile_id=9)

        result = RuntimePolicyReplayService(_shared_route_port).replay_golden_matrix(row)

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

        result = RuntimePolicyReplayService(_shared_route_port).replay_decision_logs(row, logs)

        self.assertEqual(result["runType"], "decision_log_replay")
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["passed"])
        self.assertEqual(result["result"]["logCount"], 1)
        self.assertEqual(result["result"]["changedDecisionCount"], 0)
        self.assertEqual(result["riskDeltas"]["handoffRateDelta"], 0.0)
        self.assertEqual(result["riskDeltas"]["clarificationRateDelta"], 0.0)
        self.assertEqual(result["riskDeltas"]["unsupportedActionCount"], 0)

    def test_golden_matrix_replay_uses_shared_route_port_for_candidate_profile(self) -> None:
        row = _profile_row("228.2 weighted candidate", profile_id=11)
        row["thresholds"] = {
            **dict(row["thresholds"]),
            "candidateSourceWeights": {
                "explicit_signal": 0.2,
                "mock_semantic_recall": 0.2,
                "sop_hybrid_recall": 0.2,
            },
        }
        calls: list[str] = []

        def shared_route_port(case: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
            message = str(case["turns"][-1]["message"])
            calls.append(message)
            return _shared_route_port(case, profile)

        result = RuntimePolicyReplayService(shared_route_port).replay_golden_matrix(row)

        self.assertEqual(calls, ["我要人工客服", "儿童票可以退吗", "我要退票", "机场附近打印店在哪里"])
        self.assertFalse(result["passed"])
        refund_case = next(case for case in result["result"]["cases"] if case["id"] == "sop-start")
        self.assertEqual(refund_case["actual"]["action"], "CLARIFY")
        self.assertEqual(result["failureReasons"], ["golden_matrix.failed"])

    def test_decision_log_replay_uses_shared_route_port_for_historical_comparison(self) -> None:
        row = _profile_row("228.2 historical", profile_id=12)
        row["thresholds"] = {
            **dict(row["thresholds"]),
            "candidateSourceWeights": {
                "explicit_signal": 0.2,
                "mock_semantic_recall": 0.2,
                "sop_hybrid_recall": 0.2,
            },
        }
        logs = [
            {
                "id": 32,
                "session_id": 100,
                "user_message": "我要退票",
                "final_action": "START_SOP",
                "source_layer": "sop_arbitration",
                "reason_code": "START_SOP",
                "mutates_sop_state": True,
                "handoff_triggered": False,
            }
        ]

        result = RuntimePolicyReplayService(_shared_route_port).replay_decision_logs(row, logs)

        self.assertFalse(result["passed"])
        self.assertEqual(result["result"]["changedDecisionCount"], 1)
        self.assertEqual(result["result"]["replays"][0]["actual"]["action"], "CLARIFY")

    def test_golden_matrix_replay_fails_when_shared_route_port_faults(self) -> None:
        row = _profile_row("228.2 shared fault", profile_id=13)

        def faulting_route_port(_case: dict[str, Any], _profile: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError("shared route decision fault")

        with self.assertRaisesRegex(RuntimeError, "shared route decision fault"):
            RuntimePolicyReplayService(faulting_route_port).replay_golden_matrix(row)


def _profile_row(name: str, *, profile_id: int) -> dict[str, Any]:
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


def _shared_route_port(case: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    message = str(case["turns"][-1]["message"])
    source_weights = dict(dict(row["thresholds"]).get("candidateSourceWeights") or {})
    weighted_candidate = any(float(source_weights.get(source) or 1.0) < 0.65 for source in source_weights)
    if message == "我要退票" and weighted_candidate:
        return _decision("CLARIFY", "classifier_policy", "LOW_CONFIDENCE")
    decisions = {
        "我要人工客服": _decision("HANDOFF_TO_HUMAN", "explicit_signal", "USER_REQUEST"),
        "儿童票可以退吗": _decision(
            "ANSWER_FAQ",
            "runtime_airline_faq",
            "CHILD_TICKET_REFUND",
        ),
        "我要退票": _decision("START_SOP", "post_classifier", "START_SOP"),
        "机场附近打印店在哪里": _decision("AGENT_FALLBACK", "agent_policy", "AGENT_ANSWER"),
    }
    return decisions[message]


def _decision(action: str, source_layer: str, reason_code: str) -> dict[str, Any]:
    return {
        "action": action,
        "sourceLayer": source_layer,
        "reasonCode": reason_code,
        "mutatesSopState": action in {"START_SOP", "SUSPEND_AND_START", "RESUME_TASK", "CONTINUE_ACTIVE_SOP"},
        "handoffTriggered": action == "HANDOFF_TO_HUMAN",
    }


if __name__ == "__main__":
    unittest.main()
