import time
import unittest

from fastapi.testclient import TestClient
import sqlalchemy as sa

from app.core.database import Base, get_session_factory
from app.main import app


class ExecuteWorkflowNodeIntegrationTest(unittest.TestCase):
    def test_parent_workflow_invokes_published_subworkflow_and_maps_output(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            child = _create_child_workflow(client, stamp, status="PUBLISHED")
            parent = _create_parent_workflow(client, stamp, int(child["id"]))
            response = client.post(
                f"/api/v1/workflows/{parent['id']}/runs-legacy",
                json={"input": {"ticket": "A-917"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "parent received child handled A-917"})
        self.assertGreater(data["runId"], 0)

        node_output = _node_run_output(data["runId"], "execute_workflow_1")
        self.assertEqual(node_output["childSummary"], "child handled A-917")
        self.assertEqual(node_output["status"], "SUCCEEDED")
        self.assertGreater(node_output["nestedRunId"], 0)
        self.assertGreaterEqual(node_output["latencyMs"], 0)
        self.assertEqual(node_output["mappedInputSummary"], {"ticket": "A-917"})
        self.assertEqual(node_output["mappedOutputSummary"], {"childSummary": "child handled A-917"})
        self.assertEqual(_workflow_run_status(int(node_output["nestedRunId"])), "SUCCEEDED")
        self.assertEqual(_workflow_run_count_for_workflows([int(parent["id"]), int(child["id"])]), 2)

    def test_execute_workflow_selected_node_uses_input_mapping_and_exposes_nested_run(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            child = _create_child_workflow(client, stamp, status="PUBLISHED")
            parent = _create_parent_workflow(client, stamp, int(child["id"]))
            response = client.post(
                f"/api/v1/workflows/{parent['id']}/nodes/execute_workflow_1/runs",
                json={"input": {"ticket": "B-318"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"]["childSummary"], "child handled B-318")
        self.assertEqual(data["output"]["status"], "SUCCEEDED")
        self.assertGreater(data["output"]["nestedRunId"], 0)

    def test_execute_workflow_rejects_draft_target(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            child = _create_child_workflow(client, stamp, status="DRAFT")
            parent = _create_parent_workflow(client, stamp, int(child["id"]))
            response = client.post(
                f"/api/v1/workflows/{parent['id']}/runs-legacy",
                json={"input": {"ticket": "A-000"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("published", response.json()["message"].lower())

    def test_execute_workflow_rejects_recursive_target(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            workflow = _create_self_calling_workflow(client, stamp)
            response = client.put(
                f"/api/v1/workflows/{workflow['id']}",
                json={
                    "name": workflow["name"],
                    "description": workflow["description"],
                    "status": "PUBLISHED",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                        {
                            "nodeKey": "execute_workflow_1",
                            "type": "EXECUTE_WORKFLOW",
                            "name": "Self",
                            "config": {
                                "targetWorkflowId": workflow["id"],
                                "inputMappings": [],
                                "outputMappings": [],
                                "outputParameters": [
                                    {"name": "nestedRunId", "type": "number"},
                                    {"name": "status", "type": "string"},
                                ],
                            },
                        },
                        {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final"}},
                    ],
                    "edges": [
                        {"sourceNodeKey": "start", "targetNodeKey": "execute_workflow_1", "condition": None},
                        {"sourceNodeKey": "execute_workflow_1", "targetNodeKey": "end", "condition": None},
                    ],
                },
            )
            self.assertEqual(response.status_code, 200, response.text)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"ticket": "loop"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("recursive", response.json()["message"].lower())


def _create_child_workflow(client: TestClient, stamp: int, status: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"017.4 Child {stamp}",
            "description": "published subworkflow fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "format_1",
                    "type": "TEXT_PROCESS",
                    "name": "Format",
                    "config": {
                        "operation": "format_template",
                        "template": "child handled {{start.ticket}}",
                        "outputParameters": [{"name": "summary", "type": "string"}],
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "summary", "output": "{{format_1.summary}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "format_1", "condition": None},
                {"sourceNodeKey": "format_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    child = response.json()["data"]
    if status != "DRAFT":
        update = client.put(
            f"/api/v1/workflows/{child['id']}",
            json={
                "name": child["name"],
                "description": child["description"],
                "status": status,
                "nodes": child["nodes"],
                "edges": child["edges"],
            },
        )
        assert update.status_code == 200, update.text
        child = update.json()["data"]
    return child


def _create_parent_workflow(client: TestClient, stamp: int, child_id: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"017.4 Parent {stamp}",
            "description": "execute workflow fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "execute_workflow_1",
                    "type": "EXECUTE_WORKFLOW",
                    "name": "Call Child",
                    "config": {
                        "targetWorkflowId": child_id,
                        "inputMappings": [
                            {"name": "ticket", "valueMode": "reference", "value": "{{start.ticket}}", "required": True},
                        ],
                        "outputMappings": [
                            {"source": "summary", "target": "childSummary"},
                        ],
                        "timeoutMs": 30000,
                        "maxDepth": 3,
                        "outputParameters": [
                            {"name": "childSummary", "type": "string"},
                            {"name": "nestedRunId", "type": "number"},
                            {"name": "status", "type": "string"},
                            {"name": "latencyMs", "type": "number"},
                            {"name": "mappedInputSummary", "type": "object"},
                            {"name": "mappedOutputSummary", "type": "object"},
                            {"name": "error", "type": "string"},
                        ],
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "parent received {{execute_workflow_1.childSummary}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "execute_workflow_1", "condition": None},
                {"sourceNodeKey": "execute_workflow_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_self_calling_workflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"017.4 Recursive {stamp}",
            "description": "recursive execute workflow fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final"}},
            ],
            "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _node_run_output(run_id: int, node_key: str) -> dict[str, object]:
    workflow_node_run = Base.metadata.tables["workflow_node_run"]
    with get_session_factory()() as session:
        row = session.execute(
            sa.select(workflow_node_run)
            .where(
                workflow_node_run.c.workflow_run_id == run_id,
                workflow_node_run.c.node_key == node_key,
            )
        ).mappings().one()
        return dict(row["outputs"])


def _workflow_run_status(run_id: int) -> str:
    workflow_run = Base.metadata.tables["workflow_run"]
    with get_session_factory()() as session:
        return str(session.execute(sa.select(workflow_run.c.status).where(workflow_run.c.id == run_id)).scalar_one())


def _workflow_run_count_for_workflows(workflow_ids: list[int]) -> int:
    workflow_run = Base.metadata.tables["workflow_run"]
    with get_session_factory()() as session:
        return int(
            session.execute(
                sa.select(sa.func.count())
                .select_from(workflow_run)
                .where(workflow_run.c.workflow_id.in_(workflow_ids))
            ).scalar_one()
        )


if __name__ == "__main__":
    unittest.main()
