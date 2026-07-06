import tempfile
import unittest
from pathlib import Path


class AiAssistantMemoryContextTest(unittest.TestCase):
    def test_instruction_memory_reads_recursive_nearest_agents_files(self) -> None:
        from app.modules.ai_assistant.domain.memory_context import load_instruction_memory

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "app" / "modules"
            nested.mkdir(parents=True)
            (root / "AGENTS.md").write_text("Root rule\n", encoding="utf-8")
            (root / "app" / "AGENTS.md").write_text("App rule\n", encoding="utf-8")

            memory = load_instruction_memory(root_path=root, start_path=nested)

        self.assertEqual([layer["name"] for layer in memory.layers], ["AGENTS.md", "AGENTS.md"])
        self.assertEqual([Path(layer["path"]).name for layer in memory.layers], ["AGENTS.md", "AGENTS.md"])
        self.assertIn("Root rule", memory.prompt_text)
        self.assertIn("App rule", memory.prompt_text)
        self.assertTrue(all(layer["hash"] for layer in memory.layers))

    def test_session_summary_and_working_memory_live_in_session_context(self) -> None:
        from app.modules.ai_assistant.domain.memory_context import (
            active_working_memory_items,
            invalidate_working_memory_item,
            upsert_session_summary,
            upsert_working_memory_item,
        )

        context: dict = {}
        context = upsert_session_summary(
            context,
            content="User confirmed the aviation adapter stays mock-only.",
            source_message_ids=[1, 2],
            source_event_ids=[10],
            algorithm="deterministic-test",
            token_estimate=12,
        )
        context = upsert_working_memory_item(
            context,
            key="adapter_boundary",
            value="mock-only",
            source="user-confirmed",
            status="active",
        )
        context = invalidate_working_memory_item(context, key="adapter_boundary", reason="superseded")

        memory = context["aiAssistantMemory"]
        self.assertEqual(memory["sessionSummary"]["sourceMessageIds"], [1, 2])
        self.assertEqual(memory["sessionSummary"]["sourceEventIds"], [10])
        self.assertEqual(memory["sessionSummary"]["algorithm"], "deterministic-test")
        self.assertEqual(memory["sessionSummary"]["tokenEstimate"], 12)
        self.assertTrue(memory["sessionSummary"]["hash"])
        self.assertEqual(memory["workingMemory"][0]["status"], "invalidated")
        self.assertEqual(memory["workingMemory"][0]["deleteReason"], "superseded")
        self.assertEqual(active_working_memory_items(context), [])


if __name__ == "__main__":
    unittest.main()
