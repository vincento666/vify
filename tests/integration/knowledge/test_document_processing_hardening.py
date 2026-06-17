from datetime import datetime
import os
import time
import unittest

import httpx
import sqlalchemy as sa
from sqlalchemy import inspect

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.modules.knowledge.domain.service import KnowledgeBaseService
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository


class DocumentProcessingHardeningTest(unittest.TestCase):
    def test_failed_reprocess_clears_chunks_embeddings_and_reports_outcome(self) -> None:
        kb_id = _seed_knowledge_base()
        content = b"Reset password\n\nContact support"

        with get_session_factory()() as session:
            service = KnowledgeBaseService(KnowledgeBaseRepository(session))
            document = service.upload_document(kb_id, "hardening.txt", content)
            service.process_document(document["id"], content)

            failed = service.process_document(document["id"], b"   \r\n\t")
            detail = service.get_document(document["id"])
            chunks = service.list_chunks(document["id"])

        self.assertIsNotNone(failed)
        self.assertEqual("FAILED", failed.status)
        self.assertEqual("Document is empty", failed.error_message)
        self.assertEqual(0, failed.chunk_count)
        self.assertEqual(0, failed.embedding_count)
        self.assertEqual("FAILED", detail["status"])
        self.assertEqual("Document is empty", detail["errorMessage"])
        self.assertEqual([], chunks)
        self.assertEqual(0, _embedding_count(document["id"]))

    def test_successful_reprocess_replaces_old_chunks_and_embeddings(self) -> None:
        kb_id = _seed_knowledge_base()

        with get_session_factory()() as session:
            service = KnowledgeBaseService(KnowledgeBaseRepository(session))
            document = service.upload_document(kb_id, "reprocess.txt", b"Alpha\n\nBeta")
            service.process_document(document["id"], b"Alpha\n\nBeta")

            outcome = service.process_document(document["id"], b"Gamma only")
            chunks = service.list_chunks(document["id"])

        self.assertIsNotNone(outcome)
        self.assertEqual("DONE", outcome.status)
        self.assertEqual(1, outcome.chunk_count)
        self.assertEqual(["Gamma only"], [chunk["content"] for chunk in chunks])
        embedding_count = _embedding_count(document["id"])
        self.assertEqual(embedding_count, outcome.embedding_count)
        self.assertEqual(1 if _has_durable_vector_backend() else 0, embedding_count)


def _seed_knowledge_base() -> int:
    initialise_database()
    register_baseline_tables()
    knowledge_base = Base.metadata.tables["knowledge_base"]
    now = datetime.now()
    with get_session_factory()() as session:
        kb_id = session.execute(
            knowledge_base.insert().values(
                name=f"Hardening KB {time.time_ns()}",
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(kb_id)


def _embedding_count(document_id: int) -> int:
    register_baseline_tables()
    document_chunk = Base.metadata.tables["document_chunk"]
    document_embedding = Base.metadata.tables["document_embedding"]
    with get_session_factory()() as session:
        bind = session.get_bind()
        if not inspect(bind).has_table("document_embedding"):
            return _weaviate_document_count(document_id)
        return int(
            session.execute(
                sa.select(sa.func.count())
                .select_from(document_embedding)
                .join(document_chunk, document_embedding.c.chunk_id == document_chunk.c.id)
                .where(document_chunk.c.document_id == document_id)
            ).scalar_one()
        )


def _weaviate_document_count(document_id: int) -> int:
    base_url = os.getenv("HIFY_WEAVIATE_URL")
    if not base_url:
        return 0
    response = httpx.post(
        f"{base_url.rstrip('/')}/v1/graphql",
        json={
            "query": f"""
            {{
              Aggregate {{
                HifyDocumentChunk(
                  where: {{ path: [\"document_id\"], operator: Equal, valueInt: {int(document_id)} }}
                ) {{
                  meta {{ count }}
                }}
              }}
            }}
            """
        },
        timeout=10.0,
    )
    response.raise_for_status()
    rows = response.json().get("data", {}).get("Aggregate", {}).get("HifyDocumentChunk", [])
    if not rows:
        return 0
    return int(rows[0].get("meta", {}).get("count") or 0)


def _has_durable_vector_backend() -> bool:
    with get_session_factory()() as session:
        return inspect(session.get_bind()).has_table("document_embedding") or bool(os.getenv("HIFY_WEAVIATE_URL"))


if __name__ == "__main__":
    unittest.main()
