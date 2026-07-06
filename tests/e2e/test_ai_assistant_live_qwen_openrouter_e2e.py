import os
import unittest


@unittest.skipUnless(os.getenv("OPENROUTER_API_KEY"), "OPENROUTER_API_KEY is required for real Qwen smoke")
class AiAssistantLiveQwenOpenRouterE2ETest(unittest.TestCase):
    def test_real_qwen_27b_returns_tool_calls_for_harness_planning(self) -> None:
        from app.modules.ai_assistant.domain.live_model import LivePlannerConfig, QwenLivePlanner
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        planner = QwenLivePlanner(
            LivePlannerConfig(
                base_url="https://openrouter.ai/api/v1",
                model="qwen/qwen3.6-27b",
                api_key_ref="env:OPENROUTER_API_KEY",
            )
        )

        decision = planner.plan(
            (
                "必须使用工具而不是只用文字回答。请规划以下三个动作："
                "读取 README.md；调用 tdd skill 说明红绿重构步骤；"
                "准备写入 tmp/qwen-live-smoke.txt，内容为 smoke。"
            ),
            ToolRegistry.with_builtin_tools(),
        )

        tool_names = [call["toolName"] for call in decision.tool_calls]
        self.assertEqual(decision.model, "qwen/qwen3.6-27b")
        self.assertIn("read_workspace_file", tool_names)
        self.assertIn("invoke_skill", tool_names)
        self.assertIn("write_workspace_file", tool_names)
        self.assertGreater(decision.usage["totalTokens"], 0)


if __name__ == "__main__":
    unittest.main()
