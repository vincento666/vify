import unittest
from unittest.mock import patch

from tests.support.ai_assistant_memory_repo import InMemoryAiAssistantRepository


class AiAssistantToolDurationTest(unittest.TestCase):
    def test_sub_millisecond_completed_tool_duration_is_not_reported_as_zero(self) -> None:
        from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService

        service = AiAssistantHarnessService(InMemoryAiAssistantRepository())

        with patch("app.modules.ai_assistant.domain.harness.perf_counter", side_effect=[100.0, 100.0004]):
            result = service._dispatch_tool(
                session_id=7,
                message="hello",
                tool_name="echo_context",
                payload={"message": "hello"},
            )

        self.assertEqual(result["duration_ms"], 1)


if __name__ == "__main__":
    unittest.main()
