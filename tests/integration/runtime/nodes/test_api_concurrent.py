from __future__ import annotations

import unittest
from datetime import datetime
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from tests.support.local_api import LocalApiServer

from ._helpers import (
    assert_completed_node_runs,
    assert_wave_started_before_first_completion,
    create_fanout_workflow,
    wait_for_runtime_result,
)


class RuntimeV2ApiConcurrentTest(unittest.TestCase):
    def test_three_api_call_nodes_in_same_frontier_wave_keep_outputs_and_events_isolated(self) -> None:
        node_keys = {"api_a", "api_b", "api_c"}
        server = LocalApiServer()
        server.start()
        self.addCleanup(server.stop)

        with TestClient(app) as client:
            api_resource = _create_api_resource(client, server.url)
            workflow = create_fanout_workflow(
                client,
                name_prefix="217.3 API fanout",
                nodes=[
                    _api_node("api_a", api_resource["id"], "orderA", "answer_a"),
                    _api_node("api_b", api_resource["id"], "orderB", "answer_b"),
                    _api_node("api_c", api_resource["id"], "orderC", "answer_c"),
                ],
                output_template="{{api_a.answer_a}}|{{api_b.answer_b}}|{{api_c.answer_c}}",
            )
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"orderA": "A-2173", "orderB": "B-2173", "orderC": "C-2173"}},
            ).json()["data"]
            terminal = wait_for_runtime_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(
            terminal["output"]["final"],
            "API_REAL: GET /text/orders/A-2173|API_REAL: GET /text/orders/B-2173|API_REAL: GET /text/orders/C-2173",
        )
        assert_completed_node_runs(nodes, node_keys, "API_CALL")
        assert_wave_started_before_first_completion(events, node_keys)


def _create_api_resource(client: TestClient, api_base_url: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/api-resources",
        json={
            "name": f"217.3 Orders API {datetime.now().timestamp()}",
            "description": "Runtime v2 API_CALL concurrency fixture",
            "method": "GET",
            "endpoint": f"{api_base_url}/text/orders/{{{{orderId}}}}",
            "authMode": "none",
            "headers": [{"name": "X-Test-Token", "value": "secret-token", "sensitive": True}],
            "bodyTemplate": "",
            "inputSchema": {
                "type": "object",
                "properties": {"orderId": {"type": "string"}},
                "required": ["orderId"],
            },
            "outputSchema": {"type": "object", "properties": {"body": {"type": "string"}}},
            "timeoutMs": 5000,
            "testPayload": {"orderId": "A-2173"},
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _api_node(node_key: str, api_resource_id: int, input_key: str, output_variable: str) -> dict[str, object]:
    return {
        "nodeKey": node_key,
        "type": "API_CALL",
        "name": node_key,
        "config": {
            "resourceId": f"api-resource:{api_resource_id}",
            "inputMappings": [
                {"name": "orderId", "valueMode": "reference", "value": f"{{{{start.{input_key}}}}}", "required": True},
            ],
            "outputVariable": output_variable,
        },
    }


if __name__ == "__main__":
    unittest.main()
