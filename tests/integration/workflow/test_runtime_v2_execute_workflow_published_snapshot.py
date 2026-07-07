import time
import unittest

from fastapi.testclient import TestClient
import sqlalchemy as sa

from app.core.database import Base, get_session_factory
from app.main import app


class RuntimeV2ExecuteWorkflowPublishedSnapshotTest(unittest.TestCase):
    def test_nested_execute_workflow_uses_child_published_snapshot_after_draft_edit(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            child = _create_child_workflow(client, stamp, "child-v1")
            child_version = client.post(f"/api/v1/workflows/{child['id']}/publish").json()["data"]
            _update_child_workflow(client, int(child["id"]), "child-draft-v2")
            parent = _create_parent_workflow(client, stamp, int(child["id"]))
            parent_version = client.post(f"/api/v1/workflows/{parent['id']}/publish").json()["data"]

            started = client.post(
                f"/api/v1/workflows/{parent['id']}/runs",
                json={"input": {"ticket": "SNAP-194"}, "versionId": parent_version["id"]},
            ).json()["data"]
            result = _wait_for_result(client, started["resultRef"])
            node_output = _node_run_output(int(started["runId"]), "execute_workflow_1")

        self.assertEqual(started["versionId"], parent_version["id"])
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["output"], {"final": "parent saw child-v1 for SNAP-194"})
        self.assertEqual(node_output["childSummary"], "child-v1 for SNAP-194")
        self.assertEqual(node_output["nestedVersionId"], child_version["id"])
        self.assertEqual(node_output["nestedVersion"], child_version["version"])


def _create_child_workflow(client: TestClient, stamp: int, message: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"194.4 Child {stamp}",
            "description": "runtime v2 nested child",
            "nodes": _child_nodes(message),
            "edges": _child_edges(),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _update_child_workflow(client: TestClient, workflow_id: int, message: str) -> None:
    response = client.put(
        f"/api/v1/workflows/{workflow_id}",
        json={"nodes": _child_nodes(message), "edges": _child_edges()},
    )
    assert response.status_code == 200, response.text


def _child_nodes(message: str) -> list[dict[str, object]]:
    return [
        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
        {
            "nodeKey": "format_1",
            "type": "TEXT_PROCESS",
            "name": "Format",
            "config": {
                "operation": "format_template",
                "template": f"{message} for {{{{start.ticket}}}}",
                "outputParameters": [{"name": "summary", "type": "string"}],
            },
        },
        {
            "nodeKey": "end",
            "type": "END",
            "name": "End",
            "config": {"outputVariable": "summary", "output": "{{format_1.summary}}"},
        },
    ]


def _child_edges() -> list[dict[str, object]]:
    return [
        {"sourceNodeKey": "start", "targetNodeKey": "format_1", "condition": None},
        {"sourceNodeKey": "format_1", "targetNodeKey": "end", "condition": None},
    ]


def _create_parent_workflow(client: TestClient, stamp: int, child_id: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"194.4 Parent {stamp}",
            "description": "runtime v2 nested parent",
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
                        "outputMappings": [{"source": "summary", "target": "childSummary"}],
                        "outputParameters": [
                            {"name": "childSummary", "type": "string"},
                            {"name": "nestedRunId", "type": "number"},
                            {"name": "nestedVersionId", "type": "number"},
                            {"name": "nestedVersion", "type": "number"},
                            {"name": "status", "type": "string"},
                        ],
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "parent saw {{execute_workflow_1.childSummary}}"},
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


def _wait_for_result(client: TestClient, result_ref: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(result_ref)
        latest = response.json()["data"]
        if latest["status"] in {"SUCCEEDED", "FAILED"}:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for runtime v2 result; latest={latest}")


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


if __name__ == "__main__":
    unittest.main()
