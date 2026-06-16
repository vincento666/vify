from datetime import datetime
import os
import time
import unittest

from fastapi.testclient import TestClient
import httpx
import sqlalchemy as sa
from sqlalchemy import inspect

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import DEFAULT_EMBEDDING_DIMENSIONS, register_baseline_tables
from app.main import app


class EmbeddingPipelineIntegrationTest(unittest.TestCase):
    def test_processed_document_stores_embeddings_for_each_chunk(self) -> None:
        kb_id = _seed_knowledge_base()

        with TestClient(app) as client:
            upload_response = client.post(
                f"/api/v1/knowledge-bases/{kb_id}/documents",
                files={
                    "file": (
                        "embedding-guide.txt",
                        b"Reset password\n\nContact support",
                        "text/plain",
                    )
                },
            )
            self.assertEqual(upload_response.status_code, 200)
            document = upload_response.json()["data"]

            detail_response = client.get(f"/api/v1/documents/{document['id']}")

        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()["data"]
        self.assertEqual("DONE", detail["status"])
        self.assertEqual(2, detail["chunkCount"])

        rows = _list_embeddings(document["id"])
        self.assertEqual(2, len(rows))
        self.assertEqual(["fake-local-hash-v1", "fake-local-hash-v1"], [row["embedding_model"] for row in rows])
        self.assertEqual([DEFAULT_EMBEDDING_DIMENSIONS, DEFAULT_EMBEDDING_DIMENSIONS], [row["dimension"] for row in rows])
        self.assertTrue(all(len(row["embedding"]) == DEFAULT_EMBEDDING_DIMENSIONS for row in rows))


def _seed_knowledge_base() -> int:
    initialise_database()
    register_baseline_tables()
    knowledge_base = Base.metadata.tables["knowledge_base"]
    now = datetime.now()
    with get_session_factory()() as session:
        kb_id = session.execute(
            knowledge_base.insert().values(
                name=f"Embedding KB {time.time_ns()}",
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(kb_id)


def _list_embeddings(document_id: int) -> list[dict[str, object]]:
    document_chunk = Base.metadata.tables["document_chunk"]
    document_embedding = Base.metadata.tables["document_embedding"]
    with get_session_factory()() as session:
        bind = session.get_bind()
        if not inspect(bind).has_table("document_embedding"):
            return _list_weaviate_embeddings(document_id)
        rows = session.execute(
            sa.select(document_embedding)
            .join(document_chunk, document_embedding.c.chunk_id == document_chunk.c.id)
            .where(document_chunk.c.document_id == document_id)
            .order_by(document_chunk.c.chunk_index.asc())
        ).mappings().all()
    return [dict(row) for row in rows]


def _list_weaviate_embeddings(document_id: int) -> list[dict[str, object]]:
    base_url = os.getenv("HIFY_WEAVIATE_URL")
    if not base_url:
        return []
    response = httpx.post(
        f"{base_url.rstrip('/')}/v1/graphql",
        json={
            "query": f"""
            {{
              Get {{
                HifyDocumentChunk(
                  where: {{ path: [\"document_id\"], operator: Equal, valueInt: {int(document_id)} }}
                ) {{
                  embedding_model
                  _additional {{ vector }}
                }}
              }}
            }}
            """
        },
        timeout=10.0,
    )
    response.raise_for_status()
    rows = response.json().get("data", {}).get("Get", {}).get("HifyDocumentChunk", [])
    return [
        {
            "embedding_model": row.get("embedding_model"),
            "dimension": len(row.get("_additional", {}).get("vector") or []),
            "embedding": row.get("_additional", {}).get("vector") or [],
        }
        for row in rows
    ]


if __name__ == "__main__":
    unittest.main()
