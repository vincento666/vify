import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


class WorkflowVariableAggregationAssignmentTest(unittest.TestCase):
    def test_workflow_aggregates_branch_like_values_and_assigns_flow_variable(self) -> None:
        with TestClient(app) as client:
            workflow = _create_variable_workflow(client)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"primary": "", "fallback": "vip refund"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["output"], {"final": "route=vip refund"})

    def test_chatflow_assigns_conversation_scope_for_later_node_reference(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_conversation_assignment_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"sys.query": "refund topic"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["output"], {"final": "topic=refund topic"})

    def test_variable_assign_keeps_json_text_raw_and_does_not_parse(self) -> None:
        with TestClient(app) as client:
            workflow = _create_raw_json_assignment_workflow(client)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"raw": '{"name":"Ada"}'}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["output"], {"final": 'raw={"name":"Ada"}'})


def _create_variable_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Variable Workflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "variable_aggregation_1",
                    "type": "VARIABLE_AGGREGATION",
                    "name": "变量聚合",
                    "config": {
                        "strategy": "first_non_empty",
                        "sources": [
                            {"name": "primary", "value": "{{start.primary}}"},
                            {"name": "fallback", "value": "{{start.fallback}}"},
                        ],
                        "defaultValue": "default route",
                        "outputVariable": "selected",
                    },
                },
                {
                    "nodeKey": "variable_assign_1",
                    "type": "VARIABLE_ASSIGN",
                    "name": "变量赋值",
                    "config": {
                        "targetScope": "flow",
                        "targetVariable": "route",
                        "source": "{{variable_aggregation_1.selected}}",
                        "writeMode": "set",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "route={{flow.route}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "variable_aggregation_1", "condition": None},
                {"sourceNodeKey": "variable_aggregation_1", "targetNodeKey": "variable_assign_1", "condition": None},
                {"sourceNodeKey": "variable_assign_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_conversation_assignment_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Conversation Assign Chatflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "variable_assign_1",
                    "type": "VARIABLE_ASSIGN",
                    "name": "变量赋值",
                    "config": {
                        "targetScope": "conversation",
                        "targetVariable": "topic",
                        "source": "{{start.sys.query}}",
                        "writeMode": "set",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "topic={{conversation.topic}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "variable_assign_1", "condition": None},
                {"sourceNodeKey": "variable_assign_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_raw_json_assignment_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Raw JSON Assign Workflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "variable_assign_1",
                    "type": "VARIABLE_ASSIGN",
                    "name": "变量赋值",
                    "config": {
                        "targetScope": "flow",
                        "targetVariable": "raw",
                        "source": "{{start.raw}}",
                        "writeMode": "set",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "raw={{flow.raw}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "variable_assign_1", "condition": None},
                {"sourceNodeKey": "variable_assign_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
