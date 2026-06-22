from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository


class KnowledgeFaqRuntimeIntegrationTest(unittest.TestCase):
    def test_workflow_knowledge_node_returns_structured_faq_answer(self) -> None:
        kb_id = _seed_knowledge_base_with_faq()
        with TestClient(app) as client:
            workflow = _create_knowledge_flow(client, kb_id, "WORKFLOW")
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"userMessage": "refund order"}},
            )
            debug_response = client.get(
                f"/api/v1/workflows/{workflow['id']}/runs/{response.json()['data']['runId']}/debug"
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(debug_response.status_code, 200, debug_response.text)
        data = response.json()["data"]
        self.assertEqual(data["output"]["answer"], "FAQ runtime refund answer.")
        self.assertNotIn("Knowledge mock:", str(data))
        knowledge_node = next(node for node in debug_response.json()["data"]["nodeDetails"] if node["nodeKey"] == "knowledge_1")
        self.assertEqual(knowledge_node["resourceType"], "KNOWLEDGE")
        self.assertGreaterEqual(knowledge_node["latencyMs"], 0)
        self.assertIn("FAQ runtime refund answer", knowledge_node["outputSummary"])

    def test_chatflow_knowledge_node_returns_structured_faq_answer(self) -> None:
        kb_id = _seed_knowledge_base_with_faq()
        with TestClient(app) as client:
            chatflow = _create_knowledge_flow(client, kb_id, "CHATFLOW")
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={
                    "input": {
                        "sys.query": "refund order",
                        "sys.conversation_id": f"faq-runtime-{time.time_ns()}",
                        "sys.user_id": "user-faq-runtime",
                        "sys.channel": "web",
                    }
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["output"]["answer"], "FAQ runtime refund answer.")
        self.assertNotIn("Knowledge mock:", str(data))


def _create_knowledge_flow(client: TestClient, kb_id: int, flow_type: str) -> dict[str, object]:
    endpoint = "/api/v1/chatflows" if flow_type == "CHATFLOW" else "/api/v1/workflows"
    query_variable = "sys.query" if flow_type == "CHATFLOW" else "userMessage"
    response = client.post(
        endpoint,
        json={
            "name": f"{flow_type} FAQ Runtime {time.time_ns()}",
            "description": "structured faq runtime fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "knowledge_1",
                    "type": "KNOWLEDGE",
                    "name": "Knowledge",
                    "config": {
                        "knowledgeBaseId": kb_id,
                        "query": f"{{{{start.{query_variable}}}}}",
                        "topK": 3,
                        "outputVariable": "answer",
                    },
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "knowledge_1", "condition": None},
                {"sourceNodeKey": "knowledge_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _seed_knowledge_base_with_faq() -> int:
    initialise_database()
    register_baseline_tables()
    knowledge_base = Base.metadata.tables["knowledge_base"]
    now = datetime.now()
    with get_session_factory()() as session:
        kb_id = session.execute(
            knowledge_base.insert().values(
                name=f"FAQ Runtime KB {time.time_ns()}",
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        KnowledgeBaseRepository(session).create_faq(
            {
                "knowledge_base_id": int(kb_id),
                "question": "How do I request a refund?",
                "answer": "FAQ runtime refund answer.",
                "alternative_questions": ["refund order"],
                "keywords": ["refund"],
                "category": "billing",
                "priority": 10,
                "enabled": True,
                "metadata": {},
                "source": "test",
            }
        )
    return int(kb_id)


if __name__ == "__main__":
    unittest.main()
