import unittest


class AiAssistantContextBudgetTest(unittest.TestCase):
    def test_context_budget_reports_usage_layer_share_and_warning_level(self) -> None:
        from app.modules.ai_assistant.domain.context_budget import estimate_context_budget

        budget = estimate_context_budget(
            [
                {"name": "AGENTS.md", "content": "stable project instruction"},
                {"name": "session_summary", "content": "summary " * 10},
                {"name": "working_memory", "content": "decision mock-only"},
                {"name": "recent_messages", "content": "message " * 50},
                {"name": "user_message", "content": "please continue"},
            ],
            max_context_tokens=80,
        )

        self.assertEqual(budget["usage"]["maxTokens"], 80)
        self.assertGreater(budget["usage"]["usedTokens"], 0)
        self.assertLessEqual(budget["usage"]["usedTokens"], budget["usage"]["maxTokens"])
        self.assertGreater(budget["usage"]["rawTokens"], budget["usage"]["usedTokens"])
        self.assertGreater(budget["usage"]["rawUsagePercent"], budget["usage"]["usagePercent"])
        self.assertGreater(budget["usage"]["rawUsagePercent"], 70)
        self.assertIn(budget["usage"]["warningLevel"], {"warning", "critical"})
        self.assertEqual(budget["layers"][0]["name"], "AGENTS.md")
        self.assertTrue(all("sharePercent" in layer for layer in budget["layers"]))
        self.assertTrue(any(layer["name"] == "recent_messages" for layer in budget["droppedLayers"]))
        self.assertTrue(any(layer["name"] == "AGENTS.md" for layer in budget["selectedLayers"]))
        self.assertTrue(budget["dropReasons"])

    def test_compaction_snapshot_records_raw_summary_delta_and_saved_percent(self) -> None:
        from app.modules.ai_assistant.domain.context_budget import build_compaction_snapshot

        snapshot = build_compaction_snapshot(
            raw_content="raw " * 100,
            summary="summary " * 10,
            source_message_ids=[1, 2, 3],
            source_event_ids=[7, 8],
            algorithm="deterministic-summary-v1",
        )

        self.assertGreater(snapshot["rawTokens"], snapshot["summaryTokens"])
        self.assertGreater(snapshot["savedPercent"], 0)
        self.assertEqual(snapshot["sourceMessageIds"], [1, 2, 3])
        self.assertEqual(snapshot["sourceEventIds"], [7, 8])
        self.assertEqual(snapshot["algorithm"], "deterministic-summary-v1")
        self.assertTrue(snapshot["summaryHash"])


if __name__ == "__main__":
    unittest.main()
