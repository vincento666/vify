import unittest

from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.knowledge.domain.chunks import ChunkRecord
from app.modules.knowledge.domain.retrieval import (
    RetrievalMode,
    RetrievalOptions,
    reciprocal_rank_fuse,
)
from app.modules.knowledge.domain.vector_search import SimilarChunk
from app.modules.knowledge.web.schemas import RetrievalTestRequest


class _EmbeddingProvider:
    model_name = "test-embedding"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class _Repository:
    def __init__(self) -> None:
        self.vector_calls = 0
        self.document_list_calls = 0
        self.chunk = ChunkRecord(
            id=11,
            document_id=7,
            chunk_index=0,
            content="refund policy keyword only",
            token_count=4,
        )
        self.vector_chunk = ChunkRecord(
            id=12,
            document_id=7,
            chunk_index=1,
            content="semantic renewal guidance",
            token_count=3,
        )

    def get(self, knowledge_base_id: int) -> dict[str, int]:
        return {"id": knowledge_base_id}

    def search_similar_chunks(
        self,
        knowledge_base_id: int,
        query_embedding: list[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarChunk]:
        self.vector_calls += 1
        return [SimilarChunk(chunk=self.vector_chunk, score=0.91)]

    def list_done_documents(self, knowledge_base_id: int) -> list[dict[str, int]]:
        self.document_list_calls += 1
        return [{"id": 7}]

    def list_document_chunks(self, document_id: int) -> list[ChunkRecord]:
        return [self.chunk]

    def list_enabled_faqs(self, knowledge_base_id: int) -> list[dict[str, object]]:
        return [
            {
                "id": 21,
                "question": "How do I refund?",
                "answer": "Open the refund form.",
                "alternative_questions": ["refund policy"],
                "keywords": ["refund"],
                "priority": 0,
                "metadata": {},
            }
        ]

    def search_similar_faqs(
        self,
        knowledge_base_id: int,
        query_embedding: list[float],
        model_name: str,
        top_k: int,
    ) -> list[object]:
        return []


def _facade(repository: _Repository) -> KnowledgeFacade:
    facade = KnowledgeFacade.__new__(KnowledgeFacade)
    facade._repository = repository  # type: ignore[attr-defined]
    facade._embedding_provider = _EmbeddingProvider()  # type: ignore[attr-defined]
    return facade


class RetrievalStrategyTest(unittest.TestCase):
    def test_retrieval_options_normalize_product_modes(self) -> None:
        options = RetrievalOptions.from_request(retrieval_mode="keyword", top_k=5, score_threshold=0.4, rerank=True)

        self.assertEqual(options.mode, RetrievalMode.KEYWORD)
        self.assertEqual(options.top_k, 5)
        self.assertEqual(options.min_score, 0.4)
        self.assertTrue(options.rerank)

    def test_retrieval_test_schema_accepts_strategy_controls(self) -> None:
        request = RetrievalTestRequest.model_validate(
            {
                "query": "refund policy",
                "topK": 4,
                "retrievalMode": "semantic",
                "scoreThreshold": 0.35,
                "rerank": True,
            }
        )

        self.assertEqual(request.retrieval_mode, "semantic")
        self.assertEqual(request.top_k, 4)
        self.assertEqual(request.score_threshold, 0.35)
        self.assertTrue(request.rerank)

    def test_keyword_mode_skips_vector_recall(self) -> None:
        repository = _Repository()
        results = _facade(repository).search_context(1, "refund policy", top_k=3, retrieval_mode="keyword")

        self.assertEqual(repository.vector_calls, 0)
        self.assertTrue(results)
        self.assertTrue(all(result.match_type in {"KEYWORD", "EXACT", "HYBRID"} for result in results))
        self.assertFalse(any(result.content == "semantic renewal guidance" for result in results))

    def test_semantic_mode_skips_keyword_and_faq_recall(self) -> None:
        repository = _Repository()
        results = _facade(repository).search_context(1, "refund policy", top_k=3, retrieval_mode="semantic")

        self.assertEqual(repository.vector_calls, 1)
        self.assertEqual(repository.document_list_calls, 0)
        self.assertEqual([result.match_type for result in results], ["VECTOR"])
        self.assertEqual(results[0].content, "semantic renewal guidance")

    def test_rrf_fusion_prefers_items_seen_by_multiple_recall_paths(self) -> None:
        fused = reciprocal_rank_fuse(
            [
                ["doc-semantic-only", "doc-both"],
                ["doc-both", "doc-keyword-only"],
            ],
            top_k=2,
        )

        self.assertEqual(fused[0].item, "doc-both")
        self.assertEqual([entry.item for entry in fused], ["doc-both", "doc-semantic-only"])

    def test_hybrid_rerank_uses_injected_reranker(self) -> None:
        class _ReverseReranker:
            def rerank(self, query: str, candidates: list[object], top_k: int) -> list[object]:
                return list(reversed(candidates))[:top_k]

        repository = _Repository()
        facade = _facade(repository)
        facade._reranker = _ReverseReranker()  # type: ignore[attr-defined]

        results = facade.search_context(1, "refund policy", top_k=3, retrieval_mode="hybrid", rerank=True)

        self.assertEqual("semantic renewal guidance", results[0].content)


if __name__ == "__main__":
    unittest.main()
