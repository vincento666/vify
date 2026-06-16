from datetime import datetime
import time
import unittest

from sqlalchemy import inspect

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import DEFAULT_EMBEDDING_DIMENSIONS, register_baseline_tables
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.knowledge.domain.embeddings import FAKE_EMBEDDING_MODEL
from app.modules.knowledge.domain.embeddings import FakeEmbeddingProvider
from app.modules.knowledge.domain.service import KnowledgeBaseService
from app.modules.knowledge.domain.vector_store import create_vector_store
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository


class VectorSimilaritySearchTest(unittest.TestCase):
    def test_repository_searches_by_nearest_embedding(self) -> None:
        kb_id = _seed_knowledge_base()
        content = b"Alpha support\n\nBeta billing"

        with get_session_factory()() as session:
            repository = KnowledgeBaseRepository(session)
            service = KnowledgeBaseService(repository)
            document = service.upload_document(kb_id, "vectors.txt", content)
            service.process_document(document["id"], content)
            chunks = repository.list_document_chunks(document["id"])
            _replace_document_embeddings(
                repository,
                kb_id,
                chunks,
                [_basis_vector(0), _basis_vector(1)],
                FAKE_EMBEDDING_MODEL,
                DEFAULT_EMBEDDING_DIMENSIONS,
            )

            results = _search_similar_chunks(
                repository,
                kb_id,
                _basis_vector(1),
                FAKE_EMBEDDING_MODEL,
                top_k=1,
            )

        self.assertEqual(1, len(results))
        self.assertEqual("Beta billing", results[0].chunk.content)
        self.assertAlmostEqual(1.0, results[0].score)

    def test_facade_keyword_faq_match_overrides_unrelated_vector_neighbor(self) -> None:
        kb_id = _seed_knowledge_base()
        content = b"Shipping status\n\nRefund FAQ: refund window is 7 days"
        query = "refund FAQ"

        with get_session_factory()() as session:
            repository = KnowledgeBaseRepository(session)
            service = KnowledgeBaseService(repository)
            document = service.upload_document(kb_id, "faq.txt", content)
            service.process_document(document["id"], content)
            chunks = repository.list_document_chunks(document["id"])
            query_embedding = FakeEmbeddingProvider().embed([query])[0]
            _replace_document_embeddings(
                repository,
                kb_id,
                chunks,
                [query_embedding, [-value for value in query_embedding]],
                FAKE_EMBEDDING_MODEL,
                DEFAULT_EMBEDDING_DIMENSIONS,
            )

            results = KnowledgeFacade(session).search_chunks(kb_id, query, top_k=1)

        self.assertEqual(1, len(results))
        self.assertIn("Refund FAQ", results[0].content)

    def test_facade_uses_vector_neighbor_when_keyword_confidence_is_low(self) -> None:
        kb_id = _seed_knowledge_base()
        content = b"Shipping status\n\nRefund FAQ: refund window is 7 days"
        query = "refund warranty"

        with get_session_factory()() as session:
            repository = KnowledgeBaseRepository(session)
            service = KnowledgeBaseService(repository)
            document = service.upload_document(kb_id, "low-confidence-faq.txt", content)
            service.process_document(document["id"], content)
            chunks = repository.list_document_chunks(document["id"])
            query_embedding = FakeEmbeddingProvider().embed([query])[0]
            _replace_document_embeddings(
                repository,
                kb_id,
                chunks,
                [query_embedding, [-value for value in query_embedding]],
                FAKE_EMBEDDING_MODEL,
                DEFAULT_EMBEDDING_DIMENSIONS,
            )

            results = KnowledgeFacade(session).search_chunks(kb_id, query, top_k=1)

        self.assertEqual(1, len(results))
        self.assertEqual("Shipping status", results[0].content)


def _seed_knowledge_base() -> int:
    initialise_database()
    register_baseline_tables()
    knowledge_base = Base.metadata.tables["knowledge_base"]
    now = datetime.now()
    with get_session_factory()() as session:
        kb_id = session.execute(
            knowledge_base.insert().values(
                name=f"Vector Search KB {time.time_ns()}",
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(kb_id)


def _basis_vector(index: int) -> list[float]:
    vector = [0.0] * DEFAULT_EMBEDDING_DIMENSIONS
    vector[index] = 1.0
    return vector


def _replace_document_embeddings(
    repository: KnowledgeBaseRepository,
    knowledge_base_id: int,
    chunks: list,
    embeddings: list[list[float]],
    model_name: str,
    dimensions: int,
) -> None:
    if _has_relational_vector_table(repository):
        repository.replace_document_embeddings(chunks, embeddings, model_name, dimensions)
        return
    create_vector_store(repository).replace_document_embeddings(
        knowledge_base_id,
        chunks,
        embeddings,
        model_name,
        dimensions,
    )


def _search_similar_chunks(
    repository: KnowledgeBaseRepository,
    knowledge_base_id: int,
    query_embedding: list[float],
    model_name: str,
    top_k: int,
):
    if _has_relational_vector_table(repository):
        return repository.search_similar_chunks(knowledge_base_id, query_embedding, model_name, top_k)
    return create_vector_store(repository).search_chunks(
        knowledge_base_id,
        query_embedding,
        model_name,
        top_k,
    )


def _has_relational_vector_table(repository: KnowledgeBaseRepository) -> bool:
    return inspect(repository._session.get_bind()).has_table("document_embedding")  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
