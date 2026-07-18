import unittest


class AiAssistantSecurityBoundaryTest(unittest.TestCase):
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
