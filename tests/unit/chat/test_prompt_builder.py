import unittest

try:
    from app.modules.chat.domain.prompt import PromptBuilder
except ModuleNotFoundError:
    PromptBuilder = None  # type: ignore[assignment]


class PromptBuilderTest(unittest.TestCase):
    def test_build_prompt_includes_system_history_and_current_user_message(self) -> None:
        self.assertIsNotNone(PromptBuilder)
        prompt = PromptBuilder().build(
            system_prompt="You are helpful.",
            history=[
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
            user_message="what can you do?",
        )

        self.assertIn("system: You are helpful.", prompt)
        self.assertIn("user: hello", prompt)
        self.assertIn("assistant: hi", prompt)
        self.assertTrue(prompt.endswith("user: what can you do?"))


if __name__ == "__main__":
    unittest.main()
