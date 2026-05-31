from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class AgentBindingFieldsTest(unittest.TestCase):
    def test_create_and_update_persist_nullable_knowledge_and_workflow_ids(self) -> None:
        model_id = _seed_model()
        knowledge_base_id, workflow_id = _seed_knowledge_base_and_workflow()

        with TestClient(app) as client:
            created = client.post(
                "/api/v1/agents",
                json={
                    "name": f"Binding Agent {time.time_ns()}",
                    "modelConfigId": model_id,
                    "temperature": 0.7,
                    "maxTokens": 2048,
                    "maxContextTurns": 10,
                    "toolIds": [],
                    "knowledgeBaseId": knowledge_base_id,
                    "workflowId": workflow_id,
                },
            ).json()["data"]

            self.assertEqual(created.get("knowledgeBaseId"), knowledge_base_id)
            self.assertEqual(created.get("workflowId"), workflow_id)

            listed = client.get("/api/v1/agents", params={"page": 1, "pageSize": 20}).json()["data"]["list"]
            item = next(row for row in listed if row["id"] == created["id"])
            self.assertEqual(item["knowledgeBaseId"], knowledge_base_id)
            self.assertEqual(item["workflowId"], workflow_id)

            updated = client.put(
                f"/api/v1/agents/{created['id']}",
                json={
                    "name": created["name"],
                    "modelConfigId": model_id,
                    "temperature": 0.7,
                    "maxTokens": 2048,
                    "maxContextTurns": 10,
                    "knowledgeBaseId": None,
                    "workflowId": None,
                },
            ).json()["data"]

            self.assertIsNone(updated["knowledgeBaseId"])
            self.assertIsNone(updated["workflowId"])


def _seed_model() -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Agent Binding Provider {time.time_ns()}",
                type="OPENAI",
                base_url="mock://success",
                auth_config={"api_key": "sk-test"},
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        model_id = session.execute(
            model_config.insert().values(
                provider_id=provider_id,
                name="Agent Binding Model",
                model_id="agent-binding-model",
                context_size=4096,
                extra_params={},
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(model_id)


def _seed_knowledge_base_and_workflow() -> tuple[int, int]:
    initialise_database()
    register_baseline_tables()
    knowledge_base = Base.metadata.tables["knowledge_base"]
    workflow = Base.metadata.tables["workflow"]
    now = datetime.now()
    with get_session_factory()() as session:
        knowledge_base_id = session.execute(
            knowledge_base.insert().values(
                name=f"Agent Binding KB {time.time_ns()}",
                description="binding kb fixture",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        workflow_id = session.execute(
            workflow.insert().values(
                name=f"Agent Binding Workflow {time.time_ns()}",
                description="binding workflow fixture",
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
