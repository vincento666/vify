import unittest


class AiAssistantToolSelfCorrectionPolicyTest(unittest.TestCase):
    def test_recoverable_observation_prefers_repaired_arguments_within_budget(self) -> None:
        from app.modules.ai_assistant.domain import harness

        self.assertTrue(
            hasattr(harness, "plan_tool_self_correction"),
            "harness must expose plan_tool_self_correction() for recoverable tool observations",
        )
        decision = harness.plan_tool_self_correction(
            tool_name="repairable_5xx_tool",
            tool_input={
                "caseId": "bad",
                "_selfCorrection": {"retryToolInput": {"caseId": "good"}},
            },
            observation=_recoverable_observation(code="TOOL_RUNTIME_ERROR"),
            ai_assistant_budget={"maxToolRepairAttempts": 1},
            previous_repair_attempts=0,
            risk_level="READ",
        )

        self.assertEqual(decision["action"], "retry_tool")
        self.assertEqual(decision["toolName"], "repairable_5xx_tool")
        self.assertEqual(decision["toolInput"], {"caseId": "good"})
        self.assertEqual(decision["reason"], "recoverable_tool_observation")

    def test_recoverable_rate_limit_can_select_fallback_tool(self) -> None:
        from app.modules.ai_assistant.domain import harness

        self.assertTrue(hasattr(harness, "plan_tool_self_correction"))
        decision = harness.plan_tool_self_correction(
            tool_name="rate_limited_tool",
            tool_input={
                "caseId": "rate-limit",
                "_selfCorrection": {
                    "fallbackToolName": "fallback_lookup_tool",
                    "fallbackToolInput": {"caseId": "fallback"},
                },
            },
            observation=_recoverable_observation(code="TOOL_RATE_LIMIT"),
            ai_assistant_budget={"maxToolRepairAttempts": 1},
            previous_repair_attempts=0,
            risk_level="READ",
        )

        self.assertEqual(decision["action"], "fallback_tool")
        self.assertEqual(decision["toolName"], "fallback_lookup_tool")
        self.assertEqual(decision["toolInput"], {"caseId": "fallback"})

    def test_budget_exhaustion_blocks_repair_attempt(self) -> None:
        from app.modules.ai_assistant.domain import harness

        self.assertTrue(hasattr(harness, "plan_tool_self_correction"))
        decision = harness.plan_tool_self_correction(
            tool_name="repairable_5xx_tool",
            tool_input={
                "caseId": "bad",
                "_selfCorrection": {"retryToolInput": {"caseId": "good"}},
            },
            observation=_recoverable_observation(code="TOOL_RUNTIME_ERROR"),
            ai_assistant_budget={"maxToolRepairAttempts": 0},
            previous_repair_attempts=0,
            risk_level="READ",
        )

        self.assertEqual(decision["action"], "budget_exhausted")
        self.assertEqual(decision["reason"], "tool_repair_budget_exhausted")

    def test_write_risk_is_terminal_without_explicit_human_approved_repair(self) -> None:
        from app.modules.ai_assistant.domain import harness

        self.assertTrue(hasattr(harness, "plan_tool_self_correction"))
        decision = harness.plan_tool_self_correction(
            tool_name="business_write_tool",
            tool_input={
                "caseId": "side-effect",
                "_selfCorrection": {"retryToolInput": {"caseId": "side-effect-retry"}},
            },
            observation=_recoverable_observation(code="TOOL_RUNTIME_ERROR"),
            ai_assistant_budget={"maxToolRepairAttempts": 1},
            previous_repair_attempts=0,
            risk_level="BUSINESS_WRITE",
        )

        self.assertEqual(decision["action"], "terminal")
        self.assertEqual(decision["reason"], "side_effect_repair_requires_human_approval")


def _recoverable_observation(*, code: str) -> dict[str, object]:
    return {
        "kind": "tool_error",
        "toolName": "repairable_5xx_tool",
        "error": {"code": code, "message": code, "retriable": True},
        "retriable": True,
        "modelVisible": True,
    }


if __name__ == "__main__":
    unittest.main()
