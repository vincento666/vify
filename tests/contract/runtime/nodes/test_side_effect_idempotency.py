from __future__ import annotations

import time
import unittest
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from tests.support.local_api import LocalApiServer


class RuntimeV2SideEffectProtectionContractTest(unittest.TestCase):
    def test_message_send_has_idempotency_key_and_execution_record(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(
                client,
                "217.4 message side effect",
                [_node("message_1", "MESSAGE", {"content": "notify {{start.name}}", "outputVariable": "content"})],
                "sent {{message_1.content}}",
            )
            started, terminal, nodes, events = _run_workflow(client, workflow["id"], {"name": "Ada"})

        self.assertEqual(terminal["status"], "SUCCEEDED")
        message = _node_run(nodes, "message_1")
        protection = _assert_side_effect_protection(
            message,
            run_id=int(started["runId"]),
            effect_type="message_send",
            strategy="idempotency_key",
        )
        completed = _completed_event_output(events, "message_1")
        self.assertEqual(completed["sideEffectProtection"], protection)
        self.assertEqual(_event_count(events, "workflow_node_completed", "message_1"), 1)

    def test_variable_assignment_write_has_execution_record_protection(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(
                client,
                "217.4 variable write side effect",
                [
                    _node(
                        "assign_1",
                        "VARIABLE_ASSIGN",
                        {
                            "targetScope": "conversation",
                            "targetVariable": "ticket",
                            "sourceValue": "{{start.ticket}}",
                            "outputVariable": "assignedTicket",
                        },
                    )
                ],
                "{{assign_1.assignedTicket}}",
            )
            started, terminal, nodes, events = _run_workflow(client, workflow["id"], {"ticket": "TK-2174"})

        self.assertEqual(terminal["output"]["final"], "TK-2174")
        assignment = _node_run(nodes, "assign_1")
        protection = _assert_side_effect_protection(
            assignment,
            run_id=int(started["runId"]),
            effect_type="runtime_variable_write",
            strategy="execution_record",
        )
        self.assertEqual(assignment["outputs"]["sideEffectProtection"], protection)
        self.assertEqual(_event_count(events, "workflow_node_completed", "assign_1"), 1)

    def test_external_api_call_evidence_includes_idempotency_key(self) -> None:
        server = LocalApiServer()
        server.start()
        self.addCleanup(server.stop)

        with TestClient(app) as client:
            api_resource = _create_api_resource(client, server.url)
            workflow = _create_workflow(
                client,
                "217.4 api side effect",
                [
                    _node(
                        "api_1",
                        "API_CALL",
                        {
                            "resourceId": f"api-resource:{api_resource['id']}",
                            "inputMappings": [
                                {
                                    "name": "orderId",
                                    "valueMode": "reference",
                                    "value": "{{start.orderId}}",
                                    "required": True,
                                }
                            ],
                            "outputVariable": "body",
                        },
                    )
                ],
                "{{api_1.body}}",
            )
            started, terminal, nodes, events = _run_workflow(client, workflow["id"], {"orderId": "API-2174"})

        self.assertEqual(terminal["output"]["final"], "API_REAL: GET /text/orders/API-2174")
        api_node = _node_run(nodes, "api_1")
        protection = _assert_side_effect_protection(
            api_node,
            run_id=int(started["runId"]),
            effect_type="external_api_call",
            strategy="idempotency_key",
        )
        self.assertEqual(api_node["outputs"]["evidence"]["idempotencyKey"], protection["idempotencyKey"])
        self.assertEqual(_event_count(events, "workflow_node_completed", "api_1"), 1)

    def test_transfer_to_human_interrupt_is_checkpointed_as_proposed_action(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(
                client,
                "217.4 transfer side effect",
                [
                    _node(
                        "handoff_1",
                        "TRANSFER_TO_HUMAN",
                        {
                            "message": "handoff {{start.sys.query}}",
                            "queue": "ops",
                            "reason": "customer_request",
                            "priority": "high",
                        },
                    )
                ],
                "{{handoff_1.handoff_status}}",
            )
            started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"sys.query": "need help"}},
            ).json()["data"]
            interrupted = _wait_for_result(client, started["resultRef"], wanted_status="INTERRUPTED")
            events = client.get(started["eventsRef"]).json()["data"]["list"]

        output = interrupted["output"]
        protection = output["sideEffectProtection"]
        self.assertEqual(protection["effectType"], "handoff_request")
        self.assertEqual(protection["strategy"], "proposed_action")
        self.assertEqual(protection["executionRecord"]["runId"], int(started["runId"]))
        self.assertIn(str(started["runId"]), protection["idempotencyKey"])
        self.assertEqual(output["proposedAction"]["idempotencyKey"], protection["idempotencyKey"])
        self.assertEqual(output["proposedAction"]["status"], "PENDING")
        waiting_payload = next(event["payload"] for event in events if event["type"] == "workflow_node_waiting")
        self.assertEqual(waiting_payload["sideEffectProtection"], protection)
        self.assertEqual(_event_count(events, "handoff_requested", "handoff_1"), 1)


def _run_workflow(
    client: TestClient,
    workflow_id: int,
    input_data: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    started = client.post(f"/api/v1/workflows/{workflow_id}/runs", json={"input": input_data}).json()["data"]
    terminal = _wait_for_result(client, started["resultRef"])
    nodes = client.get(started["nodesRef"]).json()["data"]["list"]
    events = client.get(started["eventsRef"]).json()["data"]["list"]
    return started, terminal, nodes, events


def _wait_for_result(client: TestClient, result_ref: str, wanted_status: str = "SUCCEEDED") -> dict[str, Any]:
    deadline = time.monotonic() + 5.0
    latest: dict[str, Any] = {}
    terminal_statuses = {"SUCCEEDED", "FAILED", "INTERRUPTED", "CANCELLED"}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] == wanted_status:
            return latest
        if latest["status"] in terminal_statuses and latest["status"] != wanted_status:
            raise AssertionError(f"Expected {wanted_status}, got {latest}")
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {wanted_status}; latest={latest}")


def _assert_side_effect_protection(
    node: dict[str, Any],
    *,
    run_id: int,
    effect_type: str,
    strategy: str,
) -> dict[str, Any]:
    protection = node["outputs"]["sideEffectProtection"]
    assert protection["effectType"] == effect_type
    assert protection["strategy"] == strategy
    assert protection["executionRecord"]["runId"] == run_id
    assert protection["executionRecord"]["nodeRunId"] == node["id"]
    assert protection["executionRecord"]["nodeKey"] == node["nodeKey"]
    assert protection["executionRecord"]["nodeType"] == node["nodeType"]
    assert str(run_id) in protection["idempotencyKey"]
    assert protection["idempotencyKey"] == f"runtime-v2:{run_id}:{node['nodeKey']}:{node['nodeType'].upper()}"
    return protection


def _node_run(nodes: list[dict[str, Any]], node_key: str) -> dict[str, Any]:
    return next(node for node in nodes if node["nodeKey"] == node_key)


def _completed_event_output(events: list[dict[str, Any]], node_key: str) -> dict[str, Any]:
    event = next(
        event
        for event in events
        if event["type"] == "workflow_node_completed" and event["nodeId"] == node_key
    )
    return event["payload"]["output"]


def _event_count(events: list[dict[str, Any]], event_type: str, node_key: str) -> int:
    return len([event for event in events if event["type"] == event_type and event["nodeId"] == node_key])


def _create_workflow(
    client: TestClient,
    name_prefix: str,
    side_effect_nodes: list[dict[str, Any]],
    final_output: str,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json=_flow_payload(name_prefix, side_effect_nodes, final_output),
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_chatflow(
    client: TestClient,
    name_prefix: str,
    side_effect_nodes: list[dict[str, Any]],
    final_output: str,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/chatflows",
        json=_flow_payload(name_prefix, side_effect_nodes, final_output),
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _flow_payload(name_prefix: str, side_effect_nodes: list[dict[str, Any]], final_output: str) -> dict[str, Any]:
    nodes = [
        _node("start", "START"),
        *side_effect_nodes,
        _node("end", "END", {"outputVariable": "final", "output": final_output}),
    ]
    return {
        "name": f"{name_prefix} {time.time_ns()}",
        "description": "runtime v2 side-effect protection contract",
        "nodes": nodes,
        "edges": [
            {"sourceNodeKey": "start", "targetNodeKey": side_effect_nodes[0]["nodeKey"], "condition": None},
            {"sourceNodeKey": side_effect_nodes[-1]["nodeKey"], "targetNodeKey": "end", "condition": None},
        ],
    }


def _node(node_key: str, node_type: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"nodeKey": node_key, "type": node_type, "name": node_key, "config": config or {}}


def _create_api_resource(client: TestClient, api_base_url: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/api-resources",
        json={
            "name": f"217.4 Orders API {time.time_ns()}",
            "description": "Runtime v2 side-effect protection fixture",
            "method": "GET",
            "endpoint": f"{api_base_url}/text/orders/{{{{orderId}}}}",
            "authMode": "none",
            "headers": [],
            "bodyTemplate": "",
            "inputSchema": {
                "type": "object",
                "properties": {"orderId": {"type": "string"}},
                "required": ["orderId"],
            },
            "outputSchema": {"type": "object", "properties": {"body": {"type": "string"}}},
            "timeoutMs": 5000,
            "testPayload": {"orderId": "API-2174"},
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
