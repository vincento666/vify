import time
import unittest

from fastapi.testclient import TestClient
import sqlalchemy as sa

from app.core.database import Base, get_session_factory
from app.main import app


class WorkflowResourcePolicyIntegrationTest(unittest.TestCase):
    def test_tool_call_missing_credential_fails_before_invocation(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            server = _create_mcp(client, f"017.5 Missing Credential {stamp}", "mock://tools?credential=missing")
            workflow = _create_tool_workflow(client, stamp, int(server["id"]))
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"orderId": "A-100"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("credential", response.json()["message"].lower())

    def test_tool_call_timeout_can_continue_and_expose_failure_evidence(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            server = _create_mcp(client, f"017.5 Timeout {stamp}", "mock://tools?elapsed=50")
            workflow = _create_tool_workflow(
                client,
                stamp,
                int(server["id"]),
                config_patch={"timeoutMs": 1, "errorBehavior": "continue"},
                end_output="success={{tool_call_1.success}} error={{tool_call_1.error}}",
            )
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"orderId": "A-101"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertIn("success=False", data["output"]["final"])
        self.assertIn("timed out", data["output"]["final"])
        node_output = _node_run_output(data["runId"], "tool_call_1")
        self.assertFalse(node_output["success"])
        self.assertEqual(node_output["evidence"]["status"], "FAILED")
        self.assertIn("timed out", node_output["evidence"]["errorMessage"])

    def test_tool_call_retries_transient_failure_and_records_attempts(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            server = _create_mcp(client, f"017.5 Retry {stamp}", "mock://tools?fail_once=true")
            workflow = _create_tool_workflow(
                client,
                stamp,
                int(server["id"]),
                config_patch={"retryCount": 1},
            )
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"orderId": "A-102"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["output"], {"final": "Order A-102 status: SHIPPED"})
        node_output = _node_run_output(data["runId"], "tool_call_1")
        self.assertEqual(node_output["evidence"]["attempts"], 2)
        self.assertEqual(node_output["evidence"]["retryCount"], 1)

    def test_tool_call_blocks_write_capable_tool_without_explicit_policy(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            server = _create_mcp(client, f"017.5 Unsafe Write {stamp}", "mock://tools")
            workflow = _create_tool_workflow(
                client,
                stamp,
                int(server["id"]),
                tool_name="refund_order",
                input_mappings=[
                    {"name": "orderId", "valueMode": "reference", "value": "{{start.orderId}}", "required": True},
                    {"name": "reason", "valueMode": "literal", "value": "policy test"},
                ],
            )
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"orderId": "A-103"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("write-capable", response.json()["message"])

    def test_tool_call_error_branch_routes_failure_to_error_path(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            server = _create_mcp(client, f"017.5 Branch {stamp}", "mock://tools")
            workflow = _create_branching_tool_workflow(client, stamp, int(server["id"]))
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"orderId": "A-104"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertIn("error branch:", data["output"]["final"])
        self.assertIn("Tool is not bound", data["output"]["final"])

    def test_workflow_graph_rejects_inline_secrets_in_resource_config(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/workflows",
                json={
                    "name": f"017.5 Secret Config {stamp}",
                    "description": "secret rejection",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                        {
                            "nodeKey": "tool_call_1",
                            "type": "TOOL_CALL",
                            "name": "Tool",
                            "config": {
                                "resourceType": "MCP_TOOL",
                                "resourceId": "mcp:1:lookup_order",
                                "serverIds": [1],
                                "toolName": "lookup_order",
                                "apiKey": "sk-inline-secret",
                            },
                        },
                        {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final"}},
                    ],
                    "edges": [
                        {"sourceNodeKey": "start", "targetNodeKey": "tool_call_1", "condition": None},
                        {"sourceNodeKey": "tool_call_1", "targetNodeKey": "end", "condition": None},
                    ],
                },
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("secret", response.json()["message"].lower())


def _create_mcp(client: TestClient, name: str, endpoint: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/mcp-servers",
        json={"name": name, "endpoint": endpoint, "description": "resource policy fixture", "enabled": True},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_tool_workflow(
    client: TestClient,
    stamp: int,
    server_id: int,
    *,
    tool_name: str = "lookup_order",
    input_mappings: list[dict[str, object]] | None = None,
    config_patch: dict[str, object] | None = None,
    end_output: str = "{{tool_call_1.result}}",
) -> dict[str, object]:
    config = {
        "resourceType": "MCP_TOOL",
        "resourceId": f"mcp:{server_id}:{tool_name}",
        "serverIds": [server_id],
        "toolName": tool_name,
        "inputMappings": input_mappings or [
            {"name": "orderId", "valueMode": "reference", "value": "{{start.orderId}}", "required": True},
        ],
        "timeoutMs": 30000,
        "retryCount": 0,
        "errorBehavior": "fail",
        "outputParameters": [
            {"name": "result", "type": "string"},
            {"name": "success", "type": "boolean"},
            {"name": "error", "type": "string"},
            {"name": "evidence", "type": "object"},
        ],
    }
    config.update(config_patch or {})
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"017.5 Tool Policy {stamp}",
            "description": "resource policy workflow",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "tool_call_1", "type": "TOOL_CALL", "name": "Tool", "config": config},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": end_output}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "tool_call_1", "condition": None},
                {"sourceNodeKey": "tool_call_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_branching_tool_workflow(client: TestClient, stamp: int, server_id: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"017.5 Branch Policy {stamp}",
            "description": "resource branch policy workflow",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "tool_call_1",
                    "type": "TOOL_CALL",
                    "name": "Tool",
                    "config": {
                        "resourceType": "MCP_TOOL",
                        "resourceId": f"mcp:{server_id}:missing_tool",
                        "serverIds": [server_id],
                        "toolName": "missing_tool",
                        "inputMappings": [],
                        "errorBehavior": "branch",
                        "outputParameters": [
                            {"name": "result", "type": "string"},
                            {"name": "success", "type": "boolean"},
                            {"name": "error", "type": "string"},
                            {"name": "route", "type": "string"},
                            {"name": "evidence", "type": "object"},
                        ],
                    },
                },
                {
                    "nodeKey": "error_message",
                    "type": "TEXT_PROCESS",
                    "name": "Error",
                    "config": {
                        "operation": "format_template",
                        "template": "error branch: {{tool_call_1.error}}",
                        "outputParameters": [{"name": "text", "type": "string"}],
                    },
                },
                {
                    "nodeKey": "success_message",
                    "type": "TEXT_PROCESS",
                    "name": "Success",
                    "config": {
                        "operation": "format_template",
                        "template": "success branch",
                        "outputParameters": [{"name": "text", "type": "string"}],
                    },
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "{{error_message.text}}{{success_message.text}}"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "tool_call_1", "condition": None},
                {"sourceNodeKey": "tool_call_1", "targetNodeKey": "error_message", "condition": "error"},
                {"sourceNodeKey": "tool_call_1", "targetNodeKey": "success_message", "condition": "success"},
                {"sourceNodeKey": "error_message", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "success_message", "targetNodeKey": "end", "condition": None},
            ],
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


if __name__ == "__main__":
    unittest.main()
