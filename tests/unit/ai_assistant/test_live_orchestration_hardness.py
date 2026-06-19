import unittest


class AiAssistantLiveOrchestrationHardnessTest(unittest.TestCase):
    def test_colloquial_file_write_then_readback_intent_supplements_missing_model_tools(self) -> None:
        from app.modules.ai_assistant.domain.harness import _supplement_required_tool_calls

        message = (
            "帮我看看 specs/README.md，查一下退票规则，按 TDD 整理，"
            "创建并写入 tmp/ai-assistant-uat-progress.md，内容为中文三段式总结，"
            "写完后再读回来确认。"
        )
        model_calls = [
            {"toolName": "read_workspace_file", "toolInput": {"path": "specs/README.md"}},
            {"toolName": "search_knowledge_base", "toolInput": {"query": "退票规则"}},
            {"toolName": "invoke_skill", "toolInput": {"skillName": "tdd", "instruction": "整理验证"}},
        ]

        supplemented = _supplement_required_tool_calls(message, model_calls)

        self.assertEqual([call["toolName"] for call in supplemented], [
            "read_workspace_file",
            "search_knowledge_base",
            "invoke_skill",
            "write_workspace_file",
            "read_workspace_file",
        ])
        self.assertEqual(supplemented[3]["toolInput"]["path"], "tmp/ai-assistant-uat-progress.md")
        self.assertIn("中文三段式总结", supplemented[3]["toolInput"]["content"])
        self.assertEqual(supplemented[4]["toolInput"]["path"], "tmp/ai-assistant-uat-progress.md")

    def test_colloquial_skill_and_knowledge_intent_supplements_missing_model_tools(self) -> None:
        from app.modules.ai_assistant.domain.harness import _supplement_required_tool_calls

        supplemented = _supplement_required_tool_calls("用 tdd 帮我查一下知识库里的退票规则", [])

        self.assertEqual([call["toolName"] for call in supplemented], ["search_knowledge_base", "invoke_skill"])
        self.assertEqual(supplemented[0]["toolInput"]["query"], "退票规则")
        self.assertEqual(supplemented[1]["toolInput"]["skillName"], "tdd")

    def test_read_only_first_round_does_not_rush_later_write_steps(self) -> None:
        from app.modules.ai_assistant.domain.harness import _supplement_required_tool_calls

        supplemented = _supplement_required_tool_calls(
            "读取 AGENTS.md，再调用 tdd skill，最后准备写入 tmp/react-loop-summary.md",
            [{"toolName": "read_workspace_file", "toolInput": {"path": "AGENTS.md"}}],
        )

        self.assertEqual([call["toolName"] for call in supplemented], ["read_workspace_file"])

    def test_colloquial_verify_after_write_means_readback(self) -> None:
        from app.modules.ai_assistant.domain.harness import _supplement_required_tool_calls

        supplemented = _supplement_required_tool_calls(
            "顺手在 tmp/ai-assistant-fuzzy-uat.md 留一份中文校验记录，写完后自己再核对一遍内容",
            [{"toolName": "write_workspace_file", "toolInput": {"path": "tmp/ai-assistant-fuzzy-uat.md", "content": "记录"}}],
        )

        self.assertEqual(
            [call["toolName"] for call in supplemented],
            ["write_workspace_file", "read_workspace_file"],
        )
        self.assertEqual(supplemented[1]["toolInput"]["path"], "tmp/ai-assistant-fuzzy-uat.md")


if __name__ == "__main__":
    unittest.main()
