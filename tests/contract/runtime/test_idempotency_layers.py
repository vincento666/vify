from __future__ import annotations

import time
import unittest
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.main import app
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository


class RuntimeV2IdempotencyLayersContractTest(unittest.TestCase):
    def test_start_idempotency_key_is_carried_into_runtime_job_payload(self) -> None:
        idempotency_key = f"runtime-v2-start-{time.time_ns()}"
        with TestClient(app) as client, patch("app.modules.workflow.web.router.threading.Thread"):
            workflow = _create_workflow(
                client,
                "218.6 job idempotency",
                [_node("message_1", "MESSAGE", {"content": "queued", "outputVariable": "content"})],
                "{{message_1.content}}",
            )
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"sys.query": "queue only"}, "idempotencyKey": idempotency_key},
            )
            self.assertEqual(response.status_code, 200, response.text)
            started = response.json()["data"]

            with get_session_factory()() as session:
                job = RuntimeJobRepository(session).get_by_run(int(started["runId"]))

        self.assertIsNotNone(job)
        payload = dict(job["payload"] or {})
        self.assertEqual(payload["runId"], int(started["runId"]))
        self.assertEqual(payload["ownerType"], "WORKFLOW")
        self.assertEqual(payload["idempotencyKey"], idempotency_key)
        self.assertEqual(payload["idempotencyLayer"], "run")

    def test_node_side_effect_idempotency_key_is_stable_across_node_run_records(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(
                client,
                "218.6 node idempotency",
                [_node("message_1", "MESSAGE", {"content": "stable", "outputVariable": "content"})],
                "{{message_1.content}}",
            )
            started, terminal, nodes, _events = _run_workflow(client, workflow["id"], {"sys.query": "stable"})

        self.assertEqual(terminal["status"], "SUCCEEDED")
        message = _node_run(nodes, "message_1")
        protection = message["outputs"]["sideEffectProtection"]
        self.assertEqual(protection["idempotencyKey"], f"runtime-v2:{started['runId']}:message_1:MESSAGE")
        self.assertEqual(protection["executionRecord"]["nodeRunId"], message["id"])

    def test_transfer_to_human_proposed_action_uses_stable_side_effect_key(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(
                client,
                "218.6 handoff idempotency",
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
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"sys.query": "need operator"}},
            )
            self.assertEqual(response.status_code, 200, response.text)
            started = response.json()["data"]
            interrupted = _wait_for_result(client, started["resultRef"], wanted_status="INTERRUPTED")

        protection = interrupted["output"]["sideEffectProtection"]
        expected_key = f"runtime-v2:{started['runId']}:handoff_1:TRANSFER_TO_HUMAN"
        self.assertEqual(protection["idempotencyKey"], expected_key)
        self.assertEqual(interrupted["output"]["proposedAction"]["idempotencyKey"], expected_key)
        self.assertEqual(interrupted["output"]["proposedAction"]["status"], "PENDING")


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


def _node_run(nodes: list[dict[str, Any]], node_key: str) -> dict[str, Any]:
    return next(node for node in nodes if node["nodeKey"] == node_key)


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
        "description": "runtime v2 idempotency layers contract",
        "nodes": nodes,
        "edges": [
            {"sourceNodeKey": "start", "targetNodeKey": side_effect_nodes[0]["nodeKey"], "condition": None},
            {"sourceNodeKey": side_effect_nodes[-1]["nodeKey"], "targetNodeKey": "end", "condition": None},
        ],
    }


def _node(node_key: str, node_type: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"nodeKey": node_key, "type": node_type, "name": node_key, "config": config or {}}


if __name__ == "__main__":
    unittest.main()
