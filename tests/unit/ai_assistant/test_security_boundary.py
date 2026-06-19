import unittest


class AiAssistantSecurityBoundaryTest(unittest.TestCase):
    def test_smart_approval_allows_read_tools_without_manual_approval(self) -> None:
        from app.modules.ai_assistant.domain.permissions import ApprovalMode, ApprovalPolicy, PermissionDecision
        from app.modules.ai_assistant.domain.tools import RiskLevel

        decision = ApprovalPolicy(environment="test").decide(
            approval_mode=ApprovalMode.SMART_APPROVAL,
            risk_level=RiskLevel.READ,
        )

        self.assertEqual(decision, PermissionDecision.AUTO_APPROVE)

    def test_high_risk_business_write_requires_approval_under_smart_approval(self) -> None:
        from app.modules.ai_assistant.domain.permissions import ApprovalMode, ApprovalPolicy, PermissionDecision
        from app.modules.ai_assistant.domain.tools import RiskLevel

        decision = ApprovalPolicy(environment="test").decide(
            approval_mode=ApprovalMode.SMART_APPROVAL,
            risk_level=RiskLevel.BUSINESS_WRITE,
        )

        self.assertEqual(decision, PermissionDecision.REQUIRE_APPROVAL)

    def test_production_always_approve_is_denied(self) -> None:
        from app.modules.ai_assistant.domain.permissions import ApprovalMode, ApprovalPolicy, PermissionDecision
        from app.modules.ai_assistant.domain.tools import RiskLevel

        decision = ApprovalPolicy(environment="production").decide(
            approval_mode=ApprovalMode.ALWAYS_APPROVE,
            risk_level=RiskLevel.BUSINESS_WRITE,
        )

        self.assertEqual(decision, PermissionDecision.DENY)

    def test_shell_like_command_is_denied_by_sandbox(self) -> None:
        from app.modules.ai_assistant.domain.sandbox import SandboxPolicy, SandboxVerdict

        decision = SandboxPolicy().evaluate("run_shell", {"command": "rm -rf /tmp/hify"})

        self.assertEqual(decision.verdict, SandboxVerdict.DENY)
        self.assertIn("shell", decision.reason)

    def test_controlled_node_command_is_allowed_by_sandbox(self) -> None:
        from app.modules.ai_assistant.domain.sandbox import SandboxPolicy, SandboxVerdict

        decision = SandboxPolicy().evaluate("run_shell", {"command": "node tmp/ai-assistant-code-save-test-uat.mjs"})

        self.assertEqual(decision.verdict, SandboxVerdict.ALLOW)
        self.assertEqual(decision.evidence["executable"], "node")

    def test_shell_operator_command_is_denied_by_sandbox(self) -> None:
        from app.modules.ai_assistant.domain.sandbox import SandboxPolicy, SandboxVerdict

        decision = SandboxPolicy().evaluate("run_shell", {"command": "node tmp/test.mjs && rm -rf tmp"})

        self.assertEqual(decision.verdict, SandboxVerdict.DENY)
        self.assertIn("shell operator", decision.reason)


if __name__ == "__main__":
    unittest.main()
