from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient
import sqlalchemy as sa

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class DocumentParserUploadTest(unittest.TestCase):
    def test_markdown_upload_exposes_normalized_chunks(self) -> None:
        kb_id = _seed_knowledge_base()

        with TestClient(app) as client:
            upload_response = client.post(
                f"/api/v1/knowledge-bases/{kb_id}/documents",
                files={
                    "file": (
                        "reset.md",
                        b"# Reset Guide\r\n\r\n- Reset password\r\n- Contact **support**",
                        "text/markdown",
                    )
                },
            )
            self.assertEqual(upload_response.status_code, 200)
            document = upload_response.json()["data"]

            chunks_response = client.get(f"/api/v1/documents/{document['id']}/chunks")

            self.assertEqual(chunks_response.status_code, 200)
            chunks = chunks_response.json()["data"]
            self.assertEqual(
                [chunk["content"] for chunk in chunks],
                ["Reset Guide", "Reset password\nContact support"],
            )

            persisted = _list_persisted_chunks(document["id"])
            self.assertEqual(
                [chunk["content"] for chunk in persisted],
                ["Reset Guide", "Reset password\nContact support"],
            )


def _seed_knowledge_base() -> int:
    initialise_database()
    register_baseline_tables()
    knowledge_base = Base.metadata.tables["knowledge_base"]
    now = datetime.now()
    with get_session_factory()() as session:
        kb_id = session.execute(
            knowledge_base.insert().values(
                name=f"Parser Upload KB {time.time_ns()}",
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(kb_id)


def _list_persisted_chunks(document_id: int) -> list[dict[str, object]]:
    document_chunk = Base.metadata.tables["document_chunk"]
    with get_session_factory()() as session:
        rows = session.execute(
            sa.select(document_chunk)
            .where(
                document_chunk.c.document_id == document_id,
                document_chunk.c.deleted.is_(False),
            )
            .order_by(document_chunk.c.chunk_index.asc())
        ).mappings().all()
    return [dict(row) for row in rows]


if __name__ == "__main__":
    unittest.main()
