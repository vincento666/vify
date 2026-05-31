from datetime import datetime
import time
import unittest

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.modules.knowledge.domain.service import KnowledgeBaseService
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository

try:
    from app.modules.knowledge.api.facade import KnowledgeFacade
except ModuleNotFoundError:
    KnowledgeFacade = None  # type: ignore[assignment]


class MockSearchFacadeTest(unittest.TestCase):
    def test_search_chunks_returns_top_k_chunks_for_knowledge_base(self) -> None:
        self.assertIsNotNone(KnowledgeFacade)
        kb_id = _seed_knowledge_base()
        content = b"Intro\n\nHow to reset password\n\nHow to contact support"

        with get_session_factory()() as session:
            service = KnowledgeBaseService(KnowledgeBaseRepository(session))
            document = service.upload_document(kb_id, "guide.txt", content)
            service.process_document(document["id"], content)

            results = KnowledgeFacade(session).search_chunks(kb_id, "reset password", top_k=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].content, "How to reset password")
        self.assertGreater(results[0].score, 0)


def _seed_knowledge_base() -> int:
    initialise_database()
    register_baseline_tables()
    knowledge_base = Base.metadata.tables["knowledge_base"]
    now = datetime.now()
    with get_session_factory()() as session:
        knowledge_base_id = session.execute(
            knowledge_base.insert().values(
                name=f"Search KB {time.time_ns()}",
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(knowledge_base_id)


if __name__ == "__main__":
    unittest.main()
