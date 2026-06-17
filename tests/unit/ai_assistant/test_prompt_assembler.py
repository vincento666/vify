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
        self.assertIn("echo_context", prompt.text)
        self.assertIn("Echo the run state.", prompt.text)


if __name__ == "__main__":
    unittest.main()
