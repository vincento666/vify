import unittest

from app.modules.provider.infra.llm_adapters import (
    AnthropicAdapterParser,
    OllamaAdapterParser,
    OpenAIAdapterParser,
)


class LlmAdapterParserTest(unittest.TestCase):
    def test_openai_sync_response_is_parsed(self) -> None:
        result = OpenAIAdapterParser().parse_chat_response(
            {
                "choices": [
                    {
                        "message": {"content": "hello"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"total_tokens": 12},
            }
        )

        self.assertEqual(result.content, "hello")
        self.assertEqual(result.finish_reason, "stop")
        self.assertEqual(result.tokens, 12)

    def test_openai_stream_deltas_are_parsed(self) -> None:
        deltas = OpenAIAdapterParser().parse_stream_lines(
            [
                'data: {"choices":[{"delta":{"content":"hel"}}]}',
                'data: {"choices":[{"delta":{"content":"lo"}}]}',
                "data: [DONE]",
            ]
        )

        self.assertEqual(deltas, ["hel", "lo"])

    def test_anthropic_and_ollama_sync_responses_are_parsed(self) -> None:
        anthropic = AnthropicAdapterParser().parse_chat_response(
            {"content": [{"type": "text", "text": "hi"}], "stop_reason": "end_turn"}
        )
        ollama = OllamaAdapterParser().parse_chat_response(
            {"message": {"content": "local"}, "done_reason": "stop"}
        )

        self.assertEqual(anthropic.content, "hi")
        self.assertEqual(anthropic.finish_reason, "end_turn")
        self.assertEqual(ollama.content, "local")
        self.assertEqual(ollama.finish_reason, "stop")


if __name__ == "__main__":
    unittest.main()
