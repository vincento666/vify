import time
import unittest
from datetime import datetime
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


class RuntimeV2ErrorRoutingIntegrationTest(unittest.TestCase):
    def test_code_node_continue_exposes_error_and_continues_default_outlet(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_error_routing_chatflow(client, error_behavior="continue")
            started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"sys.query": "continue"}},
            )
            self.assertEqual(started.status_code, 200, started.text)
            run = started.json()["data"]
            terminal = _wait_for_result(client, run["resultRef"])
            nodes = client.get(run["nodesRef"]).json()["data"]["list"]
            events = client.get(run["eventsRef"]).json()["data"]["list"]

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertIn("continued=False", terminal["output"]["final"])
        self.assertIn("division by zero", terminal["output"]["final"])
        code_node = _node(nodes, "code_1")
        self.assertEqual(code_node["status"], "COMPLETED")
        self.assertEqual(code_node["outputs"]["success"], False)
        self.assertEqual(code_node["outputs"]["errorBehavior"], "continue")
        self.assertEqual(code_node["outputs"]["evidence"]["status"], "FAILED")
        self.assertIn("division by zero", code_node["outputs"]["evidence"]["errorMessage"])
        self.assertGreaterEqual(code_node["outputs"]["evidence"]["latencyMs"], 0)
        handled = _event(events, "workflow_node_error_handled")
        self.assertEqual(handled["nodeId"], "code_1")
        self.assertEqual(handled["payload"]["errorBehavior"], "continue")

    def test_code_node_branch_routes_error_to_error_edge(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_error_routing_chatflow(client, error_behavior="branch")
            started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"sys.query": "branch"}},
            )
            self.assertEqual(started.status_code, 200, started.text)
            run = started.json()["data"]
            terminal = _wait_for_result(client, run["resultRef"])
            nodes = client.get(run["nodesRef"]).json()["data"]["list"]
            events = client.get(run["eventsRef"]).json()["data"]["list"]

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "error route: division by zero"})
        code_node = _node(nodes, "code_1")
        self.assertEqual(code_node["outputs"]["route"], "error")
        self.assertEqual(code_node["outputs"]["errorBehavior"], "branch")
        self.assertEqual(code_node["outputs"]["evidence"]["route"], "error")
        self.assertEqual(_node(nodes, "error_message")["status"], "COMPLETED")
        self.assertNotIn("success_message", {node["nodeKey"] for node in nodes})
        handled = _event(events, "workflow_node_error_handled")
        self.assertEqual(handled["payload"]["route"], "error")

    def test_agent_call_continue_exposes_error_and_continues_default_outlet(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_agent_call_error_chatflow(client)
            started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"sys.query": "agent"}},
            )
            self.assertEqual(started.status_code, 200, started.text)
            run = started.json()["data"]
            terminal = _wait_for_result(client, run["resultRef"])
            nodes = client.get(run["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertIn("agent continued=False", terminal["output"]["final"])
        self.assertIn("AGENT_CALL", terminal["output"]["final"])
        agent_node = _node(nodes, "agent_call_1")
        self.assertEqual(agent_node["status"], "COMPLETED")
        self.assertEqual(agent_node["outputs"]["errorBehavior"], "continue")
        self.assertEqual(agent_node["outputs"]["evidence"]["status"], "FAILED")


def _create_error_routing_chatflow(client: TestClient, *, error_behavior: str) -> dict[str, Any]:
    is_branch = error_behavior == "branch"
    nodes = [
        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
        {
            "nodeKey": "code_1",
            "type": "CODE",
            "name": "Failing Code",
            "config": {
                "language": "python",
                "code": "result = 1 / 0",
                "errorBehavior": error_behavior,
                "outputParameters": [
                    {"name": "success", "type": "boolean"},
                    {"name": "error", "type": "string"},
                ],
            },
        },
    ]
    edges = [{"sourceNodeKey": "start", "targetNodeKey": "code_1", "condition": None}]
    if is_branch:
        nodes.extend(
            [
                {
                    "nodeKey": "error_message",
                    "type": "MESSAGE",
                    "name": "Error Message",
                    "config": {"content": "error route: {{code_1.error}}", "outputVariable": "content"},
                },
                {
                    "nodeKey": "success_message",
                    "type": "MESSAGE",
                    "name": "Success Message",
                    "config": {"content": "success route", "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{error_message.content}}{{success_message.content}}"},
                },
            ]
        )
        edges.extend(
            [
                {"sourceNodeKey": "code_1", "targetNodeKey": "error_message", "condition": "error"},
                {"sourceNodeKey": "code_1", "targetNodeKey": "success_message", "condition": "success"},
                {"sourceNodeKey": "error_message", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "success_message", "targetNodeKey": "end", "condition": None},
            ]
        )
    else:
        nodes.append(
            {
                "nodeKey": "end",
                "type": "END",
                "name": "End",
                "config": {"outputVariable": "final", "output": "continued={{code_1.success}} error={{code_1.error}}"},
            }
        )
        edges.append({"sourceNodeKey": "code_1", "targetNodeKey": "end", "condition": None})

    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Error Routing {error_behavior} {datetime.now().timestamp()}",
            "description": "194.2 runtime v2 error routing fixture",
            "nodes": nodes,
            "edges": edges,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_agent_call_error_chatflow(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Agent Error Routing {datetime.now().timestamp()}",
            "description": "194.2 runtime v2 agent error routing fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "agent_call_1",
                    "type": "AGENT_CALL",
                    "name": "Missing Agent",
                    "config": {
                        "errorBehavior": "continue",
                        "outputParameters": [
                            {"name": "success", "type": "boolean"},
                            {"name": "error", "type": "string"},
                        ],
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {
                        "outputVariable": "final",
                        "output": "agent continued={{agent_call_1.success}} error={{agent_call_1.error}}",
                    },
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "agent_call_1", "condition": None},
                {"sourceNodeKey": "agent_call_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _wait_for_result(client: TestClient, result_ref: str, timeout: float = 5.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] in {"SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"}:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for terminal result; latest={latest}")


def _node(nodes: list[dict[str, Any]], node_key: str) -> dict[str, Any]:
    return next(node for node in nodes if node["nodeKey"] == node_key)


def _event(events: list[dict[str, Any]], event_type: str) -> dict[str, Any]:
    return next(event for event in events if event["type"] == event_type)


if __name__ == "__main__":
    unittest.main()
