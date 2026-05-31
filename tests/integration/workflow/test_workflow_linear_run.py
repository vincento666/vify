import unittest

from fastapi.testclient import TestClient
import sqlalchemy as sa

from app.core.database import Base, get_session_factory
from app.main import app


class WorkflowLinearRunTest(unittest.TestCase):
    def test_run_linear_workflow_records_run_and_node_runs(self) -> None:
        with TestClient(app) as client:
            workflow = _create_linear_workflow(client)

            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"userMessage": "reset password"}},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"]["answer"], "LLM mock: User: reset password")
        self.assertGreater(data["runId"], 0)
        self.assertEqual(_run_status(data["runId"]), "SUCCEEDED")
        self.assertEqual(_node_run_count(data["runId"]), 3)


def _create_linear_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": "Linear workflow run",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "Answer",
                    "config": {"prompt": "User: {{start.userMessage}}", "outputVariable": "answer"},
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "llm", "condition": None},
                {"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    return response.json()["data"]


def _run_status(run_id: int) -> str:
    workflow_run = Base.metadata.tables["workflow_run"]
    with get_session_factory()() as session:
        return str(
            session.execute(
                workflow_run.select().where(workflow_run.c.id == run_id)
            ).mappings().one()["status"]
        )


def _node_run_count(run_id: int) -> int:
    workflow_node_run = Base.metadata.tables["workflow_node_run"]
    with get_session_factory()() as session:
        return int(
            session.execute(
                sa.select(sa.func.count())
                .select_from(workflow_node_run)
                .where(workflow_node_run.c.workflow_run_id == run_id)
            ).scalar_one()
        )


if __name__ == "__main__":
    unittest.main()
