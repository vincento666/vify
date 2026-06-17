import unittest
from datetime import datetime, timedelta


class AiAssistantObservabilityTest(unittest.TestCase):
    def test_observability_snapshot_counts_events_tools_and_benchmark(self) -> None:
        from app.modules.ai_assistant.domain.observability import build_observability_snapshot

        started = datetime(2026, 6, 18, 8, 0, 0)
        completed = started + timedelta(milliseconds=42)

        snapshot = build_observability_snapshot(
            run={"id": 9, "status": "COMPLETED", "started_at": started, "completed_at": completed},
            events=[{"type": "run.started"}, {"type": "tool.call_completed"}, {"type": "run.completed"}],
            tool_calls=[{"tool_name": "echo_context"}],
            approvals=[],
        )

        self.assertEqual(snapshot["runId"], 9)
        self.assertEqual(snapshot["eventCount"], 3)
        self.assertEqual(snapshot["toolCallCount"], 1)
        self.assertEqual(snapshot["approvalCount"], 0)
        self.assertEqual(snapshot["usage"]["elapsedMs"], 42)
        self.assertEqual(snapshot["benchmark"]["name"], "ai_assistant_deterministic_mvp")
        self.assertTrue(snapshot["benchmark"]["passed"])


if __name__ == "__main__":
    unittest.main()
