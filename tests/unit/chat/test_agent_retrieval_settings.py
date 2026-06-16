import unittest

from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from app.modules.chat.domain.service import ChatService
from app.modules.knowledge.api.facade import KnowledgeSearchResult
from app.modules.provider.api.schemas import ModelConfigDto


class _Repository:
    pass


class _KnowledgeFacade:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str, int, str | None, float | None, bool | None]] = []

    def search_chunks(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int = 3,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> list[KnowledgeSearchResult]:
        self.calls.append((knowledge_base_id, query, top_k, retrieval_mode, score_threshold, rerank))
        return [
            KnowledgeSearchResult(knowledge_base_id * 10 + 1, 1, 0, f"KB{knowledge_base_id} high", 3, 0.9),
            KnowledgeSearchResult(knowledge_base_id * 10 + 2, 1, 1, f"KB{knowledge_base_id} low", 3, 0.2),
        ]


class AgentRetrievalSettingsTest(unittest.TestCase):
    def test_rag_content_uses_multi_kb_top_k_threshold_and_citations(self) -> None:
        knowledge = _KnowledgeFacade()
        client = FakeOpenAIChatClient()
        service = ChatService(
            _Repository(),  # type: ignore[arg-type]
            knowledge_facade=knowledge,  # type: ignore[arg-type]
            llm_client_factory=lambda _config: client,
        )
        model = ModelConfigDto(
            id=7,
            provider_id=1,
            provider_type="OPENAI",
            provider_base_url="mock://success",
            provider_auth_config={"api_key": "sk-test"},
            name="mock",
            model_id="mock-model",
            context_size=4096,
            extra_params={},
        )
        agent = {
            "system_prompt": "",
            "temperature": 0.2,
            "max_tokens": 512,
            "knowledge_base_id": 1,
            "knowledge_base_ids": [1, 2],
            "retrieval_settings": {
                "topK": 2,
                "scoreThreshold": 0.5,
                "citationStyle": "numbered",
                "retrievalMode": "keyword",
                "rerank": True,
            },
        }

        content = service._rag_content(agent, model, "refund policy", [], {})  # noqa: SLF001

        self.assertEqual(
            [
                (1, "refund policy", 2, "keyword", 0.5, True),
                (2, "refund policy", 2, "keyword", 0.5, True),
            ],
            knowledge.calls,
        )
        self.assertIn("KB1 high", client.captured_payload["messages"][-1]["content"])
        self.assertIn("KB2 high", client.captured_payload["messages"][-1]["content"])
        self.assertNotIn("KB1 low", client.captured_payload["messages"][-1]["content"])
        self.assertIn("References:", content)


if __name__ == "__main__":
    unittest.main()
