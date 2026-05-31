import unittest

from fastapi.testclient import TestClient
import sqlalchemy as sa

from app.core.database import Base, get_session_factory
from app.main import app


class WorkflowFailureBehaviorTest(unittest.TestCase):
    def test_missing_start_fails_cleanly_and_records_failed_run(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(
                client,
                nodes=[
                    {"nodeKey": "llm", "type": "LLM", "name": "Answer", "config": {"prompt": "Hello"}},
                    {"nodeKey": "end", "type": "END", "name": "End", "config": {}},
                ],
                edges=[{"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None}],
            )
            response = client.post(f"/api/v1/workflows/{workflow['id']}/runs", json={"input": {"userMessage": "hi"}})

        self.assertEqual(response.status_code, 400)
        self.assertIn("START node not found", response.json()["message"])
        self.assertEqual(_latest_run_status(int(workflow["id"])), "FAILED")

    def test_unknown_node_type_fails_cleanly_and_records_failed_run(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(
                client,
                nodes=[
                    {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                    {"nodeKey": "unknown", "type": "NOPE", "name": "Unknown", "config": {}},
                ],
                edges=[{"sourceNodeKey": "start", "targetNodeKey": "unknown", "condition": None}],
            )
            response = client.post(f"/api/v1/workflows/{workflow['id']}/runs", json={"input": {"userMessage": "hi"}})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unknown node type", response.json()["message"])
        self.assertEqual(_latest_run_status(int(workflow["id"])), "FAILED")

    def test_step_limit_fails_cleanly_and_records_failed_run(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(
                client,
                nodes=[
                    {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                    {
                        "nodeKey": "loop",
                        "type": "LLM",
                        "name": "Loop",
                        "config": {"prompt": "{{start.userMessage}}", "outputVariable": "answer"},
                    },
                ],
                edges=[
                    {"sourceNodeKey": "start", "targetNodeKey": "loop", "condition": None},
                    {"sourceNodeKey": "loop", "targetNodeKey": "loop", "condition": None},
                ],
            )
            response = client.post(f"/api/v1/workflows/{workflow['id']}/runs", json={"input": {"userMessage": "hi"}})

        self.assertEqual(response.status_code, 400)
        self.assertIn("step limit exceeded", response.json()["message"])
        self.assertEqual(_latest_run_status(int(workflow["id"])), "FAILED")


def _create_workflow(
    client: TestClient,
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": "Failure workflow",
            "description": "",
            "nodes": nodes,
            "edges": edges,
        },
    )
    return response.json()["data"]


def _latest_run_status(workflow_id: int) -> str:
    workflow_run = Base.metadata.tables["workflow_run"]
    with get_session_factory()() as session:
        row = session.execute(
            sa.select(workflow_run)
            .where(workflow_run.c.workflow_id == workflow_id)
            .order_by(workflow_run.c.id.desc())
            .limit(1)
        ).mappings().one()
    return str(row["status"])


if __name__ == "__main__":
    unittest.main()
