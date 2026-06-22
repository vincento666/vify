import time
import unittest

from fastapi.testclient import TestClient
import sqlalchemy as sa

from app.core.database import Base, get_session_factory
from app.main import app


class ChatflowExecuteWorkflowNodeIntegrationTest(unittest.TestCase):
    def test_chatflow_invokes_published_workflow_and_keeps_parent_session_state(self) -> None:
        stamp = time.time_ns()
        conversation_id = f"cf-subflow-{stamp}"
        with TestClient(app) as client:
            child = _create_child_workflow(client, stamp, status="PUBLISHED")
            chatflow = _create_parent_chatflow(client, stamp, int(child["id"]))
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={
                    "input": {
                        "ticket": "A-451",
                        "sys.query": "查询订单 A-451",
                        "sys.conversation_id": conversation_id,
                        "sys.user_id": "u-451",
                        "sys.channel": "web",
                    }
                },
            )
            session_response = client.get(f"/api/v1/chatflows/{chatflow['id']}/sessions/{conversation_id}")

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"]["final"], "客服结果 child handled A-451")
        node_output = _node_run_output(data["runId"], "execute_workflow_1")
        self.assertEqual(node_output["childSummary"], "child handled A-451")
        self.assertGreater(node_output["nestedRunId"], 0)
        self.assertEqual(node_output["status"], "SUCCEEDED")
        self.assertGreaterEqual(node_output["latencyMs"], 0)
        self.assertEqual(node_output["mappedInputSummary"], {"ticket": "A-451"})
        self.assertEqual(node_output["mappedOutputSummary"], {"childSummary": "child handled A-451"})

        self.assertEqual(session_response.status_code, 200, session_response.text)
        session = session_response.json()["data"]
        self.assertEqual(session["status"], "completed")
        self.assertEqual(session["sessionId"], conversation_id)
        self.assertIsNone(session.get("waitingEvent"))
        self.assertEqual(session["variables"]["node_outputs"]["execute_workflow_1"]["childSummary"], "child handled A-451")

    def test_chatflow_selected_execute_workflow_node_exposes_nested_evidence(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            child = _create_child_workflow(client, stamp, status="PUBLISHED")
            chatflow = _create_parent_chatflow(client, stamp, int(child["id"]))
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/nodes/execute_workflow_1/runs",
                json={"input": {"ticket": "B-452"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"]["childSummary"], "child handled B-452")
        self.assertGreater(data["output"]["nestedRunId"], 0)
        self.assertEqual(data["output"]["mappedInputSummary"], {"ticket": "B-452"})
        self.assertEqual(data["output"]["mappedOutputSummary"], {"childSummary": "child handled B-452"})

    def test_chatflow_execute_workflow_rejects_recursive_target(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_parent_chatflow(client, stamp, target_workflow_id=1)
            update = client.put(
                f"/api/v1/chatflows/{chatflow['id']}",
                json={
                    "name": chatflow["name"],
                    "description": chatflow["description"],
                    "status": "DRAFT",
                    "nodes": _parent_chatflow_nodes(int(chatflow["id"])),
                    "edges": _parent_chatflow_edges(),
                },
            )
            self.assertEqual(update.status_code, 200, update.text)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"ticket": "loop"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("recursive", response.json()["message"].lower())

    def test_chatflow_execute_workflow_rejects_zero_max_depth(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            child = _create_child_workflow(client, stamp, status="PUBLISHED")
            chatflow = _create_parent_chatflow(client, stamp, int(child["id"]), max_depth=0)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"ticket": "depth"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("maxDepth exceeded", response.json()["message"])

    def test_chatflow_execute_workflow_rejects_nested_interrupt_with_clear_error(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            child = _create_interrupting_child_workflow(client, stamp)
            chatflow = _create_parent_chatflow(client, stamp, int(child["id"]))
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"ticket": "needs-question"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("nested interrupt is not supported", response.json()["message"])


def _create_child_workflow(client: TestClient, stamp: int, status: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"022.2 Child {stamp}",
            "description": "chatflow subworkflow child",
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
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "summary", "output": "{{format_1.summary}}"}},
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


def _create_interrupting_child_workflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"022.2 Interrupt Child {stamp}",
            "description": "interrupting child workflow",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "question_1", "type": "QUESTION", "name": "Question", "config": {"question": "need more info"}},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
                {"sourceNodeKey": "question_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    child = response.json()["data"]
    update = client.put(
        f"/api/v1/workflows/{child['id']}",
        json={
            "name": child["name"],
            "description": child["description"],
            "status": "PUBLISHED",
            "nodes": child["nodes"],
            "edges": child["edges"],
        },
    )
    assert update.status_code == 200, update.text
    return update.json()["data"]


def _create_parent_chatflow(
    client: TestClient,
    stamp: int,
    target_workflow_id: int,
    max_depth: int = 3,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"022.2 Parent Chatflow {stamp}",
            "description": "chatflow execute workflow fixture",
            "nodes": _parent_chatflow_nodes(target_workflow_id, max_depth=max_depth),
            "edges": _parent_chatflow_edges(),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _parent_chatflow_nodes(target_workflow_id: int, max_depth: int = 3) -> list[dict[str, object]]:
    return [
        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
        {
            "nodeKey": "execute_workflow_1",
            "type": "EXECUTE_WORKFLOW",
            "name": "Call Workflow",
            "config": {
                "targetWorkflowId": target_workflow_id,
                "inputMappings": [
                    {"name": "ticket", "valueMode": "reference", "value": "{{start.ticket}}", "required": True},
                ],
                "outputMappings": [{"source": "summary", "target": "childSummary"}],
                "maxDepth": max_depth,
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
            "nodeKey": "message_1",
            "type": "MESSAGE",
            "name": "Message",
            "config": {"outputVariable": "content", "content": "客服结果 {{execute_workflow_1.childSummary}}"},
        },
        {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "{{message_1.content}}"}},
    ]


def _parent_chatflow_edges() -> list[dict[str, object]]:
    return [
        {"sourceNodeKey": "start", "targetNodeKey": "execute_workflow_1", "condition": None},
        {"sourceNodeKey": "execute_workflow_1", "targetNodeKey": "message_1", "condition": None},
        {"sourceNodeKey": "message_1", "targetNodeKey": "end", "condition": None},
    ]


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
