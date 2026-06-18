import unittest

from app.core.config import Settings
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient


class AiAssistantQwenLivePlannerTest(unittest.TestCase):
    def test_default_settings_target_openrouter_qwen_27b_without_key_leakage(self) -> None:
        settings = Settings(_env_file=None)

        self.assertEqual(settings.ai_assistant_openrouter_base_url, "https://openrouter.ai/api/v1")
        self.assertEqual(settings.ai_assistant_openrouter_model, "qwen/qwen3.5-27b")
        self.assertEqual(settings.ai_assistant_openrouter_api_key, "")

    def test_fake_live_planner_maps_qwen_tool_calls_to_harness_plan(self) -> None:
        from app.modules.ai_assistant.domain.live_model import LivePlannerConfig, QwenLivePlanner
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        fake_client = FakeOpenAIChatClient(
            response_payload={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "我会先读取文件，再调用技能，并把写入动作交给审批。",
                            "tool_calls": [
                                {
                                    "id": "call_read",
                                    "type": "function",
                                    "function": {
                                        "name": "read_workspace_file",
                                        "arguments": '{"path":"README.md"}',
                                    },
                                },
                                {
                                    "id": "call_skill",
                                    "type": "function",
                                    "function": {
                                        "name": "invoke_skill",
                                        "arguments": '{"skillName":"tdd","instruction":"生成红绿重构计划"}',
                                    },
                                },
                                {
                                    "id": "call_write",
                                    "type": "function",
                                    "function": {
                                        "name": "write_workspace_file",
                                        "arguments": '{"path":"tmp/ai-assistant-demo.txt","content":"demo"}',
                                    },
                                },
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
            }
        )
        planner = QwenLivePlanner(
            LivePlannerConfig(
                base_url="https://openrouter.ai/api/v1",
                model="qwen/qwen3.5-27b",
                api_key_ref="env:OPENROUTER_API_KEY",
            ),
            client=fake_client,
        )

        decision = planner.plan("请读取 README，调用 tdd skill，并准备写入摘要", ToolRegistry.with_builtin_tools())

        self.assertEqual(fake_client.captured_payload["model"], "qwen/qwen3.5-27b")
        self.assertEqual([call["toolName"] for call in decision.tool_calls], [
            "read_workspace_file",
            "invoke_skill",
            "write_workspace_file",
        ])
        self.assertEqual(decision.thought_summary, "模型已返回可展示输出。")
        self.assertIn("我会先读取文件", decision.final_answer)
        self.assertNotEqual(decision.thought_summary, decision.final_answer)
        self.assertGreaterEqual(len(decision.stream_chunks), 1)
        self.assertEqual(decision.usage["total_tokens"], 20)
        tool_names = [tool["function"]["name"] for tool in fake_client.captured_payload["tools"]]
        self.assertIn("read_workspace_file", tool_names)
        self.assertIn("write_workspace_file", tool_names)
        self.assertIn("invoke_skill", tool_names)
        self.assertIn("search_knowledge_base", tool_names)

    def test_openrouter_reasoning_becomes_thought_summary_without_visible_output_duplication(self) -> None:
        from app.modules.ai_assistant.domain.live_model import LivePlannerConfig, QwenLivePlanner
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        fake_client = FakeOpenAIChatClient(
            response_payload={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "reasoning": "需要先判断用户是否要求工具调用，再生成计划。",
                            "reasoning_details": [
                                {"type": "reasoning.text", "text": "补充思考：不应作为最终回答展示。"}
                            ],
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
            }
        )
        planner = QwenLivePlanner(
            LivePlannerConfig(
                base_url="https://openrouter.ai/api/v1",
                model="qwen/qwen3.5-27b",
                api_key_ref="env:OPENROUTER_API_KEY",
            ),
            client=fake_client,
        )

        decision = planner.plan("请先思考再回答", ToolRegistry.with_builtin_tools())

        self.assertIn("需要先判断用户是否要求工具调用", decision.thought_summary)
        self.assertIn("补充思考", decision.thought_summary)
        self.assertEqual(decision.final_answer, "")
        self.assertEqual(decision.stream_chunks, [])


if __name__ == "__main__":
    unittest.main()
