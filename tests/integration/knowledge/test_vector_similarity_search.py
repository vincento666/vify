from datetime import datetime
import time
import unittest

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import DEFAULT_EMBEDDING_DIMENSIONS, register_baseline_tables
from app.modules.knowledge.domain.embeddings import FAKE_EMBEDDING_MODEL
from app.modules.knowledge.domain.service import KnowledgeBaseService
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
            repository.replace_document_embeddings(
                chunks,
                [_basis_vector(0), _basis_vector(1)],
                FAKE_EMBEDDING_MODEL,
                DEFAULT_EMBEDDING_DIMENSIONS,
            )

            results = repository.search_similar_chunks(
                kb_id,
                _basis_vector(1),
                FAKE_EMBEDDING_MODEL,
                top_k=1,
            )

        self.assertEqual(1, len(results))
        self.assertEqual("Beta billing", results[0].chunk.content)
        self.assertAlmostEqual(1.0, results[0].score)


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


if __name__ == "__main__":
    unittest.main()
