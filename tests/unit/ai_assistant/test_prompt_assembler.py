import unittest


class AiAssistantPromptAssemblerTest(unittest.TestCase):
    def test_minimal_prompt_layers_base_tools_state_and_message(self) -> None:
        from app.modules.ai_assistant.domain.prompt import PromptAssembler
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        prompt = PromptAssembler(
            base_instruction="You are Hify AI Assistant.",
            tool_registry=ToolRegistry.with_builtin_tools(),
        ).assemble(
            user_message="Echo the run state.",
            run_state={"status": "RUNNING", "phase": "reason"},
        )

        self.assertEqual(
            [layer["name"] for layer in prompt.layers],
            ["base", "tools", "run_state", "user_message"],
        )
        self.assertIn("You are Hify AI Assistant.", prompt.text)
        self.assertIn("read_workspace_file", prompt.text)
        self.assertNotIn("echo_context", prompt.text)
        self.assertIn("Echo the run state.", prompt.text)

    def test_prompt_layers_include_project_skills_memory_and_compaction(self) -> None:
        from app.modules.ai_assistant.domain.prompt import PromptAssembler, PromptMemoryItem
        from app.modules.ai_assistant.domain.skills import SkillManifest, SkillRegistry
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        prompt = PromptAssembler(
            base_instruction="You are Hify AI Assistant.",
            tool_registry=ToolRegistry.with_builtin_tools(),
            skill_registry=SkillRegistry(
                [
                    SkillManifest(
                        name="refund_policy_reader",
                        description="Read refund policy context.",
                        trigger="refund questions",
                    )
                ]
            ),
        ).assemble(
            user_message="Can I refund this order?",
            run_state={"status": "RUNNING", "phase": "reason"},
            project_instructions="Answer in concise Chinese.",
            memory_items=[
                PromptMemoryItem(scope="session", key="passenger_tier", value="gold"),
                PromptMemoryItem(scope="run", key="last_intent", value="refund"),
            ],
            compaction_summary="Earlier turns established order TK-100.",
        )

        self.assertEqual(
            [layer["name"] for layer in prompt.layers],
            [
                "base",
                "project_instructions",
                "tools",
                "skills",
                "memory",
                "compaction",
                "run_state",
                "user_message",
            ],
        )
        self.assertIn("refund_policy_reader", prompt.text)
        self.assertIn("session.passenger_tier: gold", prompt.text)
        self.assertIn("Earlier turns established order TK-100.", prompt.text)


if __name__ == "__main__":
    unittest.main()
