import unittest
from copy import deepcopy
import json

from app.modules.runtime_policy.domain.governance import RuntimePolicyReplayService
from tests.unit.runtime_policy.test_replay_service import _profile_row


class RuntimeRouteEvalContractTest(unittest.TestCase):
    def test_missing_route_replay_port_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "route replay port is required"):
            RuntimePolicyReplayService().evaluate_route_cases(
                _profile_row("228.1 missing runner", profile_id=2280),
                [],
            )

    def test_known_gap_never_counts_as_required_pass(self) -> None:
        def route_runner(case: dict[str, object], profile: dict[str, object]) -> dict[str, object]:
            del case, profile
            return {
                "action": "CLARIFY",
                "targetSopId": None,
                "mutatesSopState": False,
            }

        result = RuntimePolicyReplayService(route_replay_port=route_runner).evaluate_route_cases(
            _profile_row("228.1 known gap", profile_id=2282),
            [
                {
                    "caseId": "known-gap-composite",
                    "caseVersion": 1,
                    "status": "known_gap",
                    "turns": [{"message": "我想退费并开发票"}],
                    "initialRouteContext": {},
                    "enabledIntentIds": ["refund_ticket", "invoice_apply"],
                    "policySnapshot": {},
                    "classifierFixture": {},
                    "expected": {
                        "recalledCandidateIds": [],
                        "finalAction": "CLARIFY",
                        "targetId": None,
                        "clarificationQuestion": None,
                        "mutatesTaskState": False,
                    },
                }
            ],
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["result"]["requiredCaseCount"], 0)
        self.assertEqual(result["result"]["knownGapCount"], 1)
        self.assertIn("route_evaluation.required_evidence_missing", result["failureReasons"])

    def test_underspecified_known_gap_invalidates_otherwise_passing_report(self) -> None:
        def route_runner(case: dict[str, object], profile: dict[str, object]) -> dict[str, object]:
            del profile
            if case["status"] == "known_gap":
                return {"action": "CLARIFY", "targetSopId": None, "mutatesSopState": False}
            return {
                "action": "START_SOP",
                "targetSopId": "refund_ticket",
                "mutatesSopState": True,
            }

        result = RuntimePolicyReplayService(route_replay_port=route_runner).evaluate_route_cases(
            _profile_row("228.1 invalid known gap", profile_id=2291),
            [
                {
                    "caseId": "valid-required",
                    "caseVersion": 1,
                    "status": "required",
                    "turns": [{"message": "我要退票"}],
                    "initialRouteContext": {},
                    "enabledIntentIds": ["refund_ticket"],
                    "policySnapshot": {},
                    "classifierFixture": {},
                    "expected": {
                        "recalledCandidateIds": [],
                        "finalAction": "START_SOP",
                        "targetId": "refund_ticket",
                        "clarificationQuestion": None,
                        "mutatesTaskState": True,
                    },
                },
                {
                    "caseId": "invalid-known-gap",
                    "caseVersion": 1,
                    "status": "known_gap",
                    "turns": [{"message": "我想退费并开发票"}],
                    "expected": {
                        "finalAction": "CLARIFY",
                        "mutatesTaskState": False,
                    },
                },
            ],
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["result"]["requiredPassedCount"], 1)
        self.assertFalse(result["result"]["cases"][1]["passed"])
        self.assertIn("route_evaluation.case_contract_invalid", result["failureReasons"])

    def test_required_case_missing_expected_evidence_fails_without_running_route(self) -> None:
        runner_calls = 0

        def route_runner(case: dict[str, object], profile: dict[str, object]) -> dict[str, object]:
            nonlocal runner_calls
            runner_calls += 1
            del case, profile
            return {"action": "START_SOP", "targetSopId": "refund_ticket", "mutatesSopState": True}

        result = RuntimePolicyReplayService(route_replay_port=route_runner).evaluate_route_cases(
            _profile_row("228.1 missing evidence", profile_id=2283),
            [
                {
                    "caseId": "missing-expected",
                    "caseVersion": 1,
                    "status": "required",
                    "turns": [{"message": "我要退票"}],
                    "initialRouteContext": {},
                    "enabledIntentIds": ["refund_ticket"],
                    "policySnapshot": {},
                    "classifierFixture": {},
                    "expected": {
                        "recalledCandidateIds": [],
                        "targetId": None,
                        "clarificationQuestion": None,
                    },
                }
            ],
        )

        self.assertFalse(result["passed"])
        self.assertEqual(runner_calls, 0)
        self.assertEqual(result["result"]["requiredFailedCount"], 1)
        self.assertEqual(
            result["result"]["cases"][0]["validationErrors"],
            ["expected.finalAction.required", "expected.mutatesTaskState.required"],
        )

    def test_report_is_versioned_deterministic_and_zero_provider_by_default(self) -> None:
        observed_turns: list[list[dict[str, object]]] = []

        def route_runner(case: dict[str, object], profile: dict[str, object]) -> dict[str, object]:
            del profile
            observed_turns.append(deepcopy(case["turns"]))
            return {
                "action": "START_SOP",
                "targetSopId": "refund_ticket",
                "mutatesSopState": True,
                "recalledCandidateIds": ["sop:refund_ticket"],
            }

        case = {
            "caseId": "multi-turn-refund",
            "caseVersion": 2,
            "status": "required",
            "turns": [{"message": "我需要帮助"}, {"message": "退票"}],
            "initialRouteContext": {"activeTask": None},
            "enabledIntentIds": ["refund_ticket"],
            "policySnapshot": {"classifierMinConfidence": 0.6},
            "classifierFixture": {"mode": "deterministic"},
            "expected": {
                "recalledCandidateIds": ["sop:refund_ticket"],
                "finalAction": "START_SOP",
                "targetId": "refund_ticket",
                "clarificationQuestion": None,
                "mutatesTaskState": True,
            },
        }
        service = RuntimePolicyReplayService(route_replay_port=route_runner)
        first = service.evaluate_route_cases(
            _profile_row("228.1 deterministic", profile_id=2284),
            [case],
        )
        second = service.evaluate_route_cases(
            _profile_row("228.1 deterministic", profile_id=2284),
            [deepcopy(case)],
        )

        self.assertTrue(first["passed"])
        self.assertEqual(first["reportVersion"], "route-eval/v1")
        self.assertEqual(first["reportHash"], second["reportHash"])
        self.assertEqual(first["metrics"]["providerUsage"], {"totalCalls": 0, "liveCalls": 0, "paidCalls": 0})
        self.assertEqual(first["metrics"]["candidateRecallAtK"], 1.0)
        self.assertEqual(first["metrics"]["stateTransitionAccuracy"], 1.0)
        self.assertEqual(first["metrics"]["actionConfusion"], {"START_SOP->START_SOP": 1})
        self.assertEqual(first["metrics"]["clarificationCaseCount"], 0)
        self.assertEqual(first["result"]["cases"][0]["caseVersion"], 2)
        self.assertEqual(observed_turns, [case["turns"], case["turns"]])

    def test_provider_usage_is_aggregated_and_live_call_fails_zero_budget(self) -> None:
        def route_runner(case: dict[str, object], profile: dict[str, object]) -> dict[str, object]:
            del case, profile
            return {
                "action": "START_SOP",
                "targetSopId": "refund_ticket",
                "mutatesSopState": True,
                "providerUsage": {"totalCalls": 1, "liveCalls": 1, "paidCalls": 0},
            }

        result = RuntimePolicyReplayService(route_replay_port=route_runner).evaluate_route_cases(
            _profile_row("228.1 provider budget", profile_id=2285),
            [
                {
                    "caseId": "provider-budget",
                    "caseVersion": 1,
                    "status": "required",
                    "turns": [{"message": "我要退票"}],
                    "initialRouteContext": {},
                    "enabledIntentIds": ["refund_ticket"],
                    "policySnapshot": {},
                    "classifierFixture": {},
                    "expected": {
                        "recalledCandidateIds": [],
                        "finalAction": "START_SOP",
                        "targetId": "refund_ticket",
                        "clarificationQuestion": None,
                        "mutatesTaskState": True,
                    },
                }
            ],
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["metrics"]["providerUsage"]["totalCalls"], 1)
        self.assertIn("route_evaluation.provider_budget_exceeded", result["failureReasons"])

    def test_inconsistent_provider_counters_fail_zero_budget(self) -> None:
        def route_runner(case: dict[str, object], profile: dict[str, object]) -> dict[str, object]:
            del case, profile
            return {
                "action": "CLARIFY",
                "targetSopId": None,
                "mutatesSopState": False,
                "providerUsage": {"totalCalls": 0, "liveCalls": 1, "paidCalls": 1},
            }

        result = RuntimePolicyReplayService(route_replay_port=route_runner).evaluate_route_cases(
            _profile_row("228.1 inconsistent provider counters", profile_id=2289),
            [
                {
                    "caseId": "provider-counter-mismatch",
                    "caseVersion": 1,
                    "status": "required",
                    "turns": [{"message": "请帮忙"}],
                    "initialRouteContext": {},
                    "enabledIntentIds": [],
                    "policySnapshot": {},
                    "classifierFixture": {},
                    "expected": {
                        "recalledCandidateIds": [],
                        "finalAction": "CLARIFY",
                        "targetId": None,
                        "clarificationQuestion": None,
                        "mutatesTaskState": False,
                    },
                }
            ],
        )

        self.assertFalse(result["passed"])
        self.assertEqual(
            result["metrics"]["providerUsage"],
            {"totalCalls": 0, "liveCalls": 1, "paidCalls": 1},
        )
        self.assertIn("route_evaluation.provider_budget_exceeded", result["failureReasons"])
        self.assertIn("route_evaluation.provider_usage_inconsistent", result["failureReasons"])

    def test_required_candidate_recall_evidence_participates_in_pass(self) -> None:
        def route_runner(case: dict[str, object], profile: dict[str, object]) -> dict[str, object]:
            del case, profile
            return {
                "action": "START_SOP",
                "targetSopId": "refund_ticket",
                "mutatesSopState": True,
                "recalledCandidateIds": ["sop:invoice_apply"],
            }

        result = RuntimePolicyReplayService(route_replay_port=route_runner).evaluate_route_cases(
            _profile_row("228.1 recall evidence", profile_id=2286),
            [
                {
                    "caseId": "recall-mismatch",
                    "caseVersion": 1,
                    "status": "required",
                    "turns": [{"message": "我要退票"}],
                    "initialRouteContext": {},
                    "enabledIntentIds": ["refund_ticket"],
                    "policySnapshot": {},
                    "classifierFixture": {},
                    "expected": {
                        "recalledCandidateIds": ["sop:refund_ticket"],
                        "finalAction": "START_SOP",
                        "targetId": "refund_ticket",
                        "clarificationQuestion": None,
                        "mutatesTaskState": True,
                    },
                }
            ],
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["metrics"]["candidateRecallAtK"], 0.0)
        self.assertEqual(result["result"]["requiredFailedCount"], 1)

    def test_runner_output_is_whitelisted_before_report_persistence(self) -> None:
        unsafe_secret_value = "-".join(("sensitive", "value"))
        unsafe_provider_value = "-".join(("provider", "payload", "value"))

        def route_runner(case: dict[str, object], profile: dict[str, object]) -> dict[str, object]:
            del case, profile
            return {
                "action": "CLARIFY",
                "targetSopId": None,
                "mutatesSopState": False,
                "apiKey": unsafe_secret_value,
                "rawProviderPayload": {"token": unsafe_provider_value},
            }

        result = RuntimePolicyReplayService(route_replay_port=route_runner).evaluate_route_cases(
            _profile_row("228.1 sanitize output", profile_id=2290),
            [
                {
                    "caseId": "unsafe-runner-output",
                    "caseVersion": 1,
                    "status": "required",
                    "turns": [{"message": "请帮忙"}],
                    "initialRouteContext": {},
                    "enabledIntentIds": [],
                    "policySnapshot": {},
                    "classifierFixture": {},
                    "expected": {
                        "recalledCandidateIds": [],
                        "finalAction": "CLARIFY",
                        "targetId": None,
                        "clarificationQuestion": None,
                        "mutatesTaskState": False,
                    },
                }
            ],
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertFalse(result["passed"])
        self.assertNotIn("apiKey", result["result"]["cases"][0]["actual"])
        self.assertNotIn("rawProviderPayload", result["result"]["cases"][0]["actual"])
        self.assertNotIn(unsafe_secret_value, serialized)
        self.assertNotIn(unsafe_provider_value, serialized)
        self.assertIn("route_evaluation.runner_output_unsafe", result["failureReasons"])

    def test_invalid_case_identity_version_status_and_turns_fail_validation(self) -> None:
        runner_calls = 0

        def route_runner(case: dict[str, object], profile: dict[str, object]) -> dict[str, object]:
            nonlocal runner_calls
            runner_calls += 1
            del case, profile
            return {"action": "CLARIFY", "mutatesSopState": False}

        result = RuntimePolicyReplayService(route_replay_port=route_runner).evaluate_route_cases(
            _profile_row("228.1 invalid contract", profile_id=2287),
            [
                {
                    "caseId": "",
                    "caseVersion": 0,
                    "status": "ignored",
                    "turns": [],
                    "expected": {
                        "finalAction": "CLARIFY",
                        "mutatesTaskState": False,
                    },
                }
            ],
        )

        self.assertFalse(result["passed"])
        self.assertEqual(runner_calls, 0)
        self.assertEqual(
            result["result"]["cases"][0]["validationErrors"],
            [
                "caseId.required",
                "caseVersion.invalid",
                "status.invalid",
                "turns.required",
            ],
        )

    def test_required_case_omitting_route_contract_fields_fails_closed(self) -> None:
        runner_calls = 0

        def route_runner(case: dict[str, object], profile: dict[str, object]) -> dict[str, object]:
            nonlocal runner_calls
            runner_calls += 1
            del case, profile
            return {"action": "CLARIFY", "mutatesSopState": False}

        result = RuntimePolicyReplayService(route_replay_port=route_runner).evaluate_route_cases(
            _profile_row("228.1 required fields", profile_id=2288),
            [
                {
                    "caseId": "underspecified-required",
                    "caseVersion": 1,
                    "status": "required",
                    "turns": [{"message": "请帮忙"}],
                    "expected": {
                        "finalAction": "CLARIFY",
                        "mutatesTaskState": False,
                    },
                }
            ],
        )

        self.assertFalse(result["passed"])
        self.assertEqual(runner_calls, 0)
        self.assertEqual(
            result["result"]["cases"][0]["validationErrors"],
            [
                "initialRouteContext.required",
                "enabledIntentIds.required",
                "policySnapshot.required",
                "classifierFixture.required",
                "expected.recalledCandidateIds.required",
                "expected.targetId.required",
                "expected.clarificationQuestion.required",
            ],
        )

    def test_wrong_injected_route_result_fails_required_case(self) -> None:
        def wrong_route_runner(case: dict[str, object], profile: dict[str, object]) -> dict[str, object]:
            del case, profile
            return {
                "action": "CLARIFY",
                "sourceLayer": "post_classifier",
                "reasonCode": "WRONG_SHARED_RESULT",
                "mutatesSopState": False,
            }

        service = RuntimePolicyReplayService(route_replay_port=wrong_route_runner)
        result = service.evaluate_route_cases(
            _profile_row("228.1 wrong runner", profile_id=2281),
            [
                {
                    "caseId": "required-refund",
                    "caseVersion": 1,
                    "status": "required",
                    "turns": [{"message": "我要退票"}],
                    "initialRouteContext": {},
                    "enabledIntentIds": ["refund_ticket"],
                    "policySnapshot": {},
                    "classifierFixture": {},
                    "expected": {
                        "recalledCandidateIds": [],
                        "finalAction": "START_SOP",
                        "targetId": "refund_ticket",
                        "clarificationQuestion": None,
                        "mutatesTaskState": True,
                    },
                }
            ],
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["result"]["requiredPassedCount"], 0)
        self.assertEqual(result["result"]["requiredFailedCount"], 1)
        self.assertEqual(result["result"]["cases"][0]["actual"]["reasonCode"], "WRONG_SHARED_RESULT")


if __name__ == "__main__":
    unittest.main()
