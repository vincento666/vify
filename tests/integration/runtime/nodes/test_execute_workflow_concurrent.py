from __future__ import annotations

import time
import unittest

from fastapi.testclient import TestClient

from app.main import app

from ._helpers import (
    assert_completed_node_runs,
    assert_wave_started_before_first_completion,
    create_fanout_workflow,
    wait_for_runtime_result,
)


class RuntimeV2ExecuteWorkflowConcurrentTest(unittest.TestCase):
    def test_three_execute_workflow_nodes_in_same_frontier_wave_keep_outputs_and_events_isolated(self) -> None:
        node_keys = {"exec_a", "exec_b", "exec_c"}
        stamp = time.time_ns()
        with TestClient(app) as client:
            child = _create_child_workflow(client, stamp)
            client.post(f"/api/v1/workflows/{child['id']}/publish")
            workflow = create_fanout_workflow(
                client,
                name_prefix="217.3 Execute Workflow fanout",
                nodes=[
                    _execute_workflow_node("exec_a", child["id"], "ticketA", "childSummaryA"),
                    _execute_workflow_node("exec_b", child["id"], "ticketB", "childSummaryB"),
                    _execute_workflow_node("exec_c", child["id"], "ticketC", "childSummaryC"),
                ],
                output_template="{{exec_a.childSummaryA}}|{{exec_b.childSummaryB}}|{{exec_c.childSummaryC}}",
            )
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"ticketA": "A-2173", "ticketB": "B-2173", "ticketC": "C-2173"}},
            ).json()["data"]
            terminal = wait_for_runtime_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["output"]["final"], "child A-2173|child B-2173|child C-2173")
        assert_completed_node_runs(nodes, node_keys, "EXECUTE_WORKFLOW")
        assert_wave_started_before_first_completion(events, node_keys)


def _create_child_workflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"217.3 Child {stamp}",
            "description": "runtime v2 nested child",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "format_1",
                    "type": "TEXT_PROCESS",
                    "name": "Format",
                    "config": {
                        "operation": "format_template",
                        "template": "child {{start.ticket}}",
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
    return response.json()["data"]


def _execute_workflow_node(node_key: str, child_id: int, input_key: str, output_variable: str) -> dict[str, object]:
    return {
        "nodeKey": node_key,
        "type": "EXECUTE_WORKFLOW",
        "name": node_key,
        "config": {
            "targetWorkflowId": child_id,
            "inputMappings": [
                {"name": "ticket", "valueMode": "reference", "value": f"{{{{start.{input_key}}}}}", "required": True},
            ],
            "outputMappings": [{"source": "summary", "target": output_variable}],
            "outputParameters": [
                {"name": output_variable, "type": "string"},
                {"name": "nestedRunId", "type": "number"},
                {"name": "status", "type": "string"},
            ],
        },
    }


if __name__ == "__main__":
    unittest.main()
