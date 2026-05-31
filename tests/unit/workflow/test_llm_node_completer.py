import unittest

from app.modules.workflow.domain.context import ExecutionContext
from app.modules.workflow.domain.engine import LlmNodeExecutor


class RecordingLlmCompleter:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def complete_prompt(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return f"real llm: {prompt}"


class LlmNodeCompleterTest(unittest.TestCase):
    def test_llm_node_uses_injected_completer_when_available(self) -> None:
        completer = RecordingLlmCompleter()
        context = ExecutionContext()
        context.set_output("start", {"userMessage": "reset password"})

        result = LlmNodeExecutor(completer).execute(
            {
                "node_key": "llm",
                "type": "LLM",
                "config": {"prompt": "User: {{start.userMessage}}", "outputVariable": "answer"},
            },
            context,
        )

        self.assertEqual(result, {"answer": "real llm: User: reset password"})
        self.assertEqual(completer.prompts, ["User: reset password"])


if __name__ == "__main__":
    unittest.main()
