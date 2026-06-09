from datetime import datetime
import io
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.knowledge.domain.service import KnowledgeBaseService
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository


class StructuredFaqKnowledgeIntegrationTest(unittest.TestCase):
    def test_faq_crud_import_export_and_source_aware_retrieval(self) -> None:
        kb_id = _seed_knowledge_base()
        _seed_processed_document(kb_id, "Refund document chunk says refunds are reviewed within 30 days.")

        with TestClient(app) as client:
            created = client.post(
                f"/api/v1/knowledge-bases/{kb_id}/faqs",
                json={
                    "question": "How do I request a refund?",
                    "answer": "Use the refund form within 7 days.",
                    "alternativeQuestions": ["refund order", "money back"],
                    "keywords": ["refund", "money"],
                    "category": "billing",
                    "priority": 10,
                    "enabled": True,
                    "metadata": {"channel": "web"},
                    "source": "manual",
                },
            )
            self.assertEqual(created.status_code, 200, created.text)
            faq = created.json()["data"]

            listed = client.get(f"/api/v1/knowledge-bases/{kb_id}/faqs?pageSize=20")
            self.assertEqual(listed.status_code, 200, listed.text)
            self.assertEqual(listed.json()["data"]["list"][0]["question"], "How do I request a refund?")

            updated = client.put(
                f"/api/v1/knowledge-faqs/{faq['id']}",
                json={"answer": "Use the refund form within 14 days.", "priority": 20},
            )
            self.assertEqual(updated.status_code, 200, updated.text)
            self.assertEqual(updated.json()["data"]["answer"], "Use the refund form within 14 days.")

            imported = client.post(
                f"/api/v1/knowledge-bases/{kb_id}/faqs/import-csv",
                files={"file": ("faq.csv", b"question,answer,keywords\nShipping ETA?,Ships in 48 hours,shipping|eta\n", "text/csv")},
            )
            self.assertEqual(imported.status_code, 200, imported.text)
            self.assertEqual(imported.json()["data"]["imported"], 1)

            exported = client.get(f"/api/v1/knowledge-bases/{kb_id}/faqs/export-csv")
            self.assertEqual(exported.status_code, 200, exported.text)
            self.assertIn("Shipping ETA?", exported.text)

            retrieval = client.post(
                f"/api/v1/knowledge-bases/{kb_id}/retrieval-test",
                json={"query": "refund order", "topK": 3},
            )
            self.assertEqual(retrieval.status_code, 200, retrieval.text)

        hits = retrieval.json()["data"]["hits"]
        self.assertGreaterEqual(len(hits), 2)
        self.assertEqual(hits[0]["sourceType"], "FAQ")
        self.assertIn(hits[0]["matchType"], {"EXACT", "KEYWORD", "HYBRID"})
        self.assertEqual(hits[0]["answer"], "Use the refund form within 14 days.")
        self.assertTrue(any(hit["sourceType"] == "DOCUMENT_CHUNK" for hit in hits))

        context_hits = KnowledgeFacade(get_session_factory()()).search_context(kb_id, "refund order", top_k=3)
        self.assertEqual(context_hits[0].source_type, "FAQ")
        self.assertEqual(context_hits[0].answer, "Use the refund form within 14 days.")
        compatible = KnowledgeFacade(get_session_factory()()).search_chunks(kb_id, "refund order", top_k=1)
        self.assertIn("Use the refund form within 14 days.", compatible[0].content)

    def test_disabled_faq_is_not_returned(self) -> None:
        kb_id = _seed_knowledge_base()
        with TestClient(app) as client:
            faq = client.post(
                f"/api/v1/knowledge-bases/{kb_id}/faqs",
                json={"question": "Hidden?", "answer": "Hidden answer", "enabled": False},
            )
            self.assertEqual(faq.status_code, 200, faq.text)
            retrieval = client.post(
                f"/api/v1/knowledge-bases/{kb_id}/retrieval-test",
                json={"query": "Hidden?", "topK": 3},
            )
        self.assertEqual(retrieval.status_code, 200, retrieval.text)
        self.assertFalse(retrieval.json()["data"]["hits"])

    def test_retrieval_test_respects_keyword_mode(self) -> None:
        kb_id = _seed_knowledge_base()
        _seed_processed_document(kb_id, "refund policy keyword only")

        with TestClient(app) as client:
            retrieval = client.post(
                f"/api/v1/knowledge-bases/{kb_id}/retrieval-test",
                json={"query": "refund policy", "topK": 3, "retrievalMode": "keyword"},
            )

        self.assertEqual(retrieval.status_code, 200, retrieval.text)
        data = retrieval.json()["data"]
        self.assertEqual(data["retrievalMode"], "keyword")
        self.assertTrue(data["hits"])
        self.assertTrue(all(hit["matchType"] != "VECTOR" for hit in data["hits"]))


def _seed_knowledge_base() -> int:
    initialise_database()
    register_baseline_tables()
    knowledge_base = Base.metadata.tables["knowledge_base"]
    now = datetime.now()
    with get_session_factory()() as session:
        knowledge_base_id = session.execute(
            knowledge_base.insert().values(
                name=f"FAQ KB {time.time_ns()}",
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(knowledge_base_id)


def _seed_processed_document(kb_id: int, text: str) -> None:
    content = io.BytesIO(text.encode("utf-8")).getvalue()
    with get_session_factory()() as session:
        service = KnowledgeBaseService(KnowledgeBaseRepository(session))
        document = service.upload_document(kb_id, "faq-doc.txt", content)
        service.process_document(document["id"], content)


if __name__ == "__main__":
    unittest.main()
