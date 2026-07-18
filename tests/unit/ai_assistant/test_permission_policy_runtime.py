import unittest


class AiAssistantPermissionPolicyRuntimeTest(unittest.TestCase):
    def test_session_policy_deny_beats_always_approve_for_shell_tool(self) -> None:
        from app.modules.ai_assistant.domain.permissions import ApprovalMode, PermissionDecision
        from app.modules.ai_assistant.domain.policy_runtime import (
            PermissionPolicyRule,
            SessionPermissionPolicy,
        )
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        manifest = ToolRegistry.with_builtin_tools().get_manifest("run_shell")
        policy = SessionPermissionPolicy(
            default_decision="require_approval",
            rules=[
                PermissionPolicyRule(
                    rule_id="deny-shell",
                    match={"tool": "run_shell"},
                    effect="deny",
                    reason="shell disabled for this session",
                )
            ],
        )

        decision = policy.evaluate(
            session_id=10,
            run_id=20,
            tool_name="run_shell",
            manifest=manifest,
            tool_input={"command": "node tmp/ok.mjs"},
            approval_mode=ApprovalMode.ALWAYS_APPROVE,
        )

        self.assertEqual(decision.decision, PermissionDecision.DENY)
        self.assertEqual(decision.event["type"], "permission.evaluated")
        self.assertEqual(decision.event["payload"]["sessionId"], 10)
        self.assertEqual(decision.event["payload"]["runId"], 20)
        self.assertEqual(decision.event["payload"]["toolName"], "run_shell")
        self.assertEqual(decision.event["payload"]["riskLevel"], "EXTERNAL_SIDE_EFFECT")
        self.assertEqual(decision.event["payload"]["approvalMode"], "always_approve")
        self.assertEqual(decision.event["payload"]["decision"], "deny")
        self.assertEqual(decision.event["payload"]["matchedRuleId"], "deny-shell")
        self.assertEqual(decision.event["payload"]["reason"], "shell disabled for this session")

    def test_session_policy_can_allow_read_without_approval_but_require_write(self) -> None:
        from app.modules.ai_assistant.domain.permissions import ApprovalMode, PermissionDecision
        from app.modules.ai_assistant.domain.policy_runtime import (
            PermissionPolicyRule,
            SessionPermissionPolicy,
        )
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        registry = ToolRegistry.with_demo_tools()
        policy = SessionPermissionPolicy(
            default_decision="require_approval",
            rules=[
                PermissionPolicyRule(
                    rule_id="allow-read",
                    match={"risk": "READ"},
                    effect="allow",
                    reason="read-only tools are safe for this session",
                )
            ],
        )

        read = policy.evaluate(
            session_id=10,
            run_id=21,
            tool_name="echo_context",
            manifest=registry.get_manifest("echo_context"),
            tool_input={"message": "hello"},
            approval_mode=ApprovalMode.SMART_APPROVAL,
        )
        write = policy.evaluate(
            session_id=10,
            run_id=21,
            tool_name="write_workspace_file",
            manifest=registry.get_manifest("write_workspace_file"),
            tool_input={"path": "a.txt", "content": "x"},
            approval_mode=ApprovalMode.ALWAYS_APPROVE,
        )

        self.assertEqual(read.decision, PermissionDecision.AUTO_APPROVE)
        self.assertEqual(read.event["payload"]["matchedRuleId"], "allow-read")
        self.assertEqual(write.decision, PermissionDecision.REQUIRE_APPROVAL)
        self.assertEqual(write.event["payload"]["matchedRuleId"], "default")

    def test_session_policy_denies_when_rule_budget_limit_is_exceeded(self) -> None:
        from app.modules.ai_assistant.domain.permissions import ApprovalMode, PermissionDecision
        from app.modules.ai_assistant.domain.policy_runtime import (
            PermissionPolicyRule,
            SessionPermissionPolicy,
        )
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        policy = SessionPermissionPolicy(
            default_decision="allow",
            rules=[
                PermissionPolicyRule(
                    rule_id="budget-shell",
                    match={"tool": "run_shell"},
                    effect="allow",
                    reason="shell allowed while budget remains",
                    budget_limit=100,
                )
            ],
        )

        decision = policy.evaluate(
            session_id=10,
            run_id=22,
            tool_name="run_shell",
            manifest=ToolRegistry.with_builtin_tools().get_manifest("run_shell"),
            tool_input={"command": "node tmp/ok.mjs"},
            approval_mode=ApprovalMode.ALWAYS_APPROVE,
            current_budget=101,
        )

        self.assertEqual(decision.decision, PermissionDecision.DENY)
        self.assertEqual(decision.event["payload"]["decision"], "deny")
        self.assertEqual(decision.event["payload"]["matchedRuleId"], "budget-shell")
        self.assertEqual(decision.event["payload"]["budgetLimit"], 100)
        self.assertEqual(decision.event["payload"]["currentBudget"], 101)


if __name__ == "__main__":
    unittest.main()
