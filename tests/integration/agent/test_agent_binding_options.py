from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class AgentBindingOptionsTest(unittest.TestCase):
    def test_list_knowledge_bases_and_workflows_for_agent_binding(self) -> None:
        knowledge_base_id, workflow_id = _seed_knowledge_base_and_workflow()

        with TestClient(app) as client:
            kb_response = client.get("/api/v1/knowledge-bases", params={"page": 1, "pageSize": 20})
            workflow_response = client.get("/api/v1/workflows", params={"page": 1, "pageSize": 20})

        self.assertEqual(kb_response.status_code, 200)
        kb_ids = [item["id"] for item in kb_response.json()["data"]["list"]]
        self.assertIn(knowledge_base_id, kb_ids)

        self.assertEqual(workflow_response.status_code, 200)
        workflow_ids = [item["id"] for item in workflow_response.json()["data"]["list"]]
        self.assertIn(workflow_id, workflow_ids)


def _seed_knowledge_base_and_workflow() -> tuple[int, int]:
    initialise_database()
    register_baseline_tables()
    knowledge_base = Base.metadata.tables["knowledge_base"]
    workflow = Base.metadata.tables["workflow"]
    now = datetime.now()
    with get_session_factory()() as session:
        knowledge_base_id = session.execute(
            knowledge_base.insert().values(
                name=f"Agent Option KB {time.time_ns()}",
                description="agent binding option kb",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        workflow_id = session.execute(
            workflow.insert().values(
                name=f"Agent Option Workflow {time.time_ns()}",
                description="agent binding option workflow",
                status="DRAFT",
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(knowledge_base_id), int(workflow_id)


if __name__ == "__main__":
    unittest.main()
