import json
import unittest
from unittest.mock import patch

from app.modules.chat.domain.llm_request import FakeOpenAIChatClient


class AiAssistantMemoryExtractionTest(unittest.TestCase):
    def test_old_worker_finally_does_not_remove_new_scope_owner(self) -> None:
        from app.modules.ai_assistant.web import router

        scope_key = "alice\0workspace-a"
        old_owner = object()
        new_owner = object()

        class _Coordinator:
            def __init__(self, **_kwargs: object) -> None:
                pass

            def drain(self) -> list[object]:
                return []

        with router._MEMORY_EXTRACTION_LOCK:
            router._MEMORY_EXTRACTION_IN_FLIGHT[scope_key] = new_owner
            router._MEMORY_EXTRACTION_REQUESTED.discard(scope_key)
        try:
            with patch.object(router, "MemoryExtractionCoordinator", _Coordinator):
                router._run_memory_extraction(
                    scope_key,
                    old_owner,
                    object(),
                    object(),
                    object(),
                    object(),
                    object(),
                )
            with router._MEMORY_EXTRACTION_LOCK:
                self.assertIs(router._MEMORY_EXTRACTION_IN_FLIGHT[scope_key], new_owner)
        finally:
            with router._MEMORY_EXTRACTION_LOCK:
                router._MEMORY_EXTRACTION_IN_FLIGHT.pop(scope_key, None)
                router._MEMORY_EXTRACTION_REQUESTED.discard(scope_key)

    def test_model_extractor_returns_only_safe_durable_facts(self) -> None:
        from app.modules.ai_assistant.domain.live_model import LivePlannerConfig
        from app.modules.ai_assistant.domain.memory_extraction import ModelMemoryExtractor

        client = FakeOpenAIChatClient(
            response_payload={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(
                                {
                                    "facts": [
                                        "Prefers concise Chinese output.",
                                        "api_key=do-not-store-this-value",
                                    ]
                                }
                            ),
                        }
                    }
                ]
            }
        )
        extractor = ModelMemoryExtractor(
            LivePlannerConfig(
                base_url="mock://memory",
                model="fake-memory-model",
                api_key="test-only",
            ),
            client=client,
        )
        runs = [
            {
                "id": index,
                "input_payload": {"message": f"user-{index}"},
                "response_payload": {"finalAnswer": f"assistant-{index}"},
            }
            for index in range(1, 4)
        ]

        facts = extractor.extract(runs)

        self.assertEqual(facts, ["Prefers concise Chinese output."])
        self.assertEqual(client.captured_payload["temperature"], 0)
        self.assertEqual(client.captured_payload["response_format"], {"type": "json_object"})
        transcript = json.loads(client.captured_payload["messages"][1]["content"])
        self.assertEqual([item["runId"] for item in transcript], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
