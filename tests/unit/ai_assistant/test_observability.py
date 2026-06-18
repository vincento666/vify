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

    def test_observability_uses_real_model_usage_from_run_payload(self) -> None:
        from app.modules.ai_assistant.domain.observability import build_observability_snapshot

        started = datetime(2026, 6, 18, 8, 0, 0)
        completed = started + timedelta(milliseconds=7)

        snapshot = build_observability_snapshot(
            run={
                "id": 10,
                "status": "COMPLETED",
                "started_at": started,
                "completed_at": completed,
                "response_payload": {
                    "model": {
                        "usage": {
                            "prompt_tokens": 12,
                            "completion_tokens": 8,
                            "total_tokens": 20,
                        }
                    }
                },
            },
            events=[],
            tool_calls=[],
            approvals=[],
        )

        self.assertEqual(snapshot["usage"]["inputTokens"], 12)
        self.assertEqual(snapshot["usage"]["outputTokens"], 8)
        self.assertEqual(snapshot["usage"]["totalTokens"], 20)
        self.assertFalse(snapshot["usage"]["estimated"])

    def test_observability_falls_back_to_model_usage_events(self) -> None:
        from app.modules.ai_assistant.domain.observability import build_observability_snapshot

        started = datetime(2026, 6, 18, 8, 0, 0)
        completed = started + timedelta(milliseconds=9)

        snapshot = build_observability_snapshot(
            run={"id": 11, "status": "WAITING_APPROVAL", "started_at": started, "completed_at": completed},
            events=[
                {
                    "type": "model.call_completed",
                    "payload": {"usage": {"inputTokens": 4, "outputTokens": 3, "totalTokens": 7}},
                }
            ],
            tool_calls=[],
            approvals=[{"status": "PENDING"}],
        )

        self.assertEqual(snapshot["usage"]["inputTokens"], 4)
        self.assertEqual(snapshot["usage"]["outputTokens"], 3)
        self.assertEqual(snapshot["usage"]["totalTokens"], 7)
        self.assertFalse(snapshot["usage"]["estimated"])


if __name__ == "__main__":
    unittest.main()
