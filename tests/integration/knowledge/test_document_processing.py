from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class DocumentProcessingTest(unittest.TestCase):
    def test_document_detail_processes_pending_document_and_exposes_chunks(self) -> None:
        kb_id = _seed_knowledge_base()

        with TestClient(app) as client:
            upload_response = client.post(
                f"/api/v1/knowledge-bases/{kb_id}/documents",
                files={
                    "file": (
                        "guide.txt",
                        b"Intro\n\nHow to reset password\n\nHow to contact support",
                        "text/plain",
                    )
                },
            )
            self.assertEqual(upload_response.status_code, 200)
            created = upload_response.json()["data"]
            self.assertEqual(created["status"], "PENDING")

            detail_response = client.get(f"/api/v1/documents/{created['id']}")

            self.assertEqual(detail_response.status_code, 200)
            processed = detail_response.json()["data"]
            self.assertEqual(processed["status"], "DONE")
            self.assertEqual(processed["chunkCount"], 3)

            chunks_response = client.get(f"/api/v1/documents/{created['id']}/chunks")
            self.assertEqual(chunks_response.status_code, 200)
            chunks = chunks_response.json()["data"]
            self.assertEqual([chunk["chunkIndex"] for chunk in chunks], [0, 1, 2])
            self.assertEqual([chunk["content"] for chunk in chunks], [
                "Intro",
                "How to reset password",
                "How to contact support",
            ])
            self.assertTrue(all(chunk["tokenCount"] >= 1 for chunk in chunks))


def _seed_knowledge_base() -> int:
    initialise_database()
    register_baseline_tables()
    knowledge_base = Base.metadata.tables["knowledge_base"]
    now = datetime.now()
    with get_session_factory()() as session:
        kb_id = session.execute(
            knowledge_base.insert().values(
                name=f"Processing KB {time.time_ns()}",
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(kb_id)


if __name__ == "__main__":
    unittest.main()
