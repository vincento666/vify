import unittest

from pgvector.sqlalchemy import Vector

from app.core.database import Base
from app.core.schema import DEFAULT_EMBEDDING_DIMENSIONS, register_baseline_tables
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.knowledge.domain.vector_search import SimilarFaq


class _EmbeddingProvider:
    model_name = "test-embedding"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.3, 0.7] for _ in texts]


class _Repository:
    def __init__(self) -> None:
        self.faq_vector_calls = 0

    def get(self, knowledge_base_id: int) -> dict[str, int]:
        return {"id": knowledge_base_id}

    def list_enabled_faqs(self, knowledge_base_id: int) -> list[dict[str, object]]:
        return []

    def search_similar_faqs(
        self,
        knowledge_base_id: int,
        query_embedding: list[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarFaq]:
        self.faq_vector_calls += 1
        return [
            SimilarFaq(
                faq={
                    "id": 91,
                    "question": "How do I request a refund?",
                    "answer": "Open the refund form.",
                    "metadata": {"source": "faq-vector"},
                },
                score=0.88,
            )
        ]


def _facade(repository: _Repository) -> KnowledgeFacade:
    facade = KnowledgeFacade.__new__(KnowledgeFacade)
    facade._repository = repository  # type: ignore[attr-defined]
    facade._embedding_provider = _EmbeddingProvider()  # type: ignore[attr-defined]
    return facade


class FaqVectorProductizationTest(unittest.TestCase):
    def setUp(self) -> None:
        register_baseline_tables()

    def test_faq_embedding_table_uses_pgvector_shape(self) -> None:
        table = Base.metadata.tables["knowledge_faq_embedding"]

        self.assertEqual(
            {
                "id",
                "faq_id",
                "embedding_model",
                "embedding",
                "dimension",
                "metadata",
                "deleted",
                "created_at",
                "updated_at",
            },
            set(table.columns.keys()),
        )
        self.assertIsInstance(table.c.embedding.type, Vector)
        self.assertEqual(DEFAULT_EMBEDDING_DIMENSIONS, table.c.embedding.type.dim)
        self.assertIn("idx_knowledge_faq_embedding_faq_id", {index.name for index in table.indexes})
        self.assertIn("idx_knowledge_faq_embedding_vector_cosine", {index.name for index in table.indexes})

    def test_faq_mode_uses_faq_vector_recall_when_available(self) -> None:
        repository = _Repository()

        results = _facade(repository).search_context(1, "money back request", top_k=2, retrieval_mode="faq")

        self.assertEqual(repository.faq_vector_calls, 1)
        self.assertEqual(results[0].source_type, "FAQ")
        self.assertEqual(results[0].match_type, "VECTOR")
        self.assertEqual(results[0].answer, "Open the refund form.")


if __name__ == "__main__":
    unittest.main()
