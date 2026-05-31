from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class DocumentUploadTest(unittest.TestCase):
    def test_upload_document_creates_pending_document_and_lists_it(self) -> None:
        kb_id = _seed_knowledge_base()

        with TestClient(app) as client:
            upload_response = client.post(
                f"/api/v1/knowledge-bases/{kb_id}/documents",
                files={"file": ("guide.txt", b"hello document", "text/plain")},
            )

            self.assertEqual(upload_response.status_code, 200)
            created = upload_response.json()["data"]
            self.assertEqual(created["knowledgeBaseId"], kb_id)
            self.assertEqual(created["name"], "guide.txt")
            self.assertEqual(created["fileType"], "txt")
            self.assertEqual(created["status"], "PENDING")

            list_response = client.get(
                f"/api/v1/knowledge-bases/{kb_id}/documents",
                params={"page": 1, "pageSize": 20},
            )
            docs = list_response.json()["data"]["list"]
            self.assertTrue(any(doc["id"] == created["id"] for doc in docs))


def _seed_knowledge_base() -> int:
    initialise_database()
    register_baseline_tables()
    knowledge_base = Base.metadata.tables["knowledge_base"]
    now = datetime.now()
    with get_session_factory()() as session:
        kb_id = session.execute(
            knowledge_base.insert().values(
                name=f"Upload KB {time.time_ns()}",
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
