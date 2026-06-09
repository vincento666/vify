import unittest

from fastapi.testclient import TestClient

from app.main import app
from tests.support.local_api import LocalApiServer


class WorkflowConditionRunTest(unittest.TestCase):
    def test_condition_node_selects_matching_branch_or_default_branch(self) -> None:
        server = LocalApiServer()
        server.start()
        self.addCleanup(server.stop)
        with TestClient(app) as client:
            workflow = _create_condition_workflow(client, server.url)

            vip_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"userMessage": "hello", "intent": "vip"}},
            )
            vip_debug_response = client.get(
                f"/api/v1/workflows/{workflow['id']}/runs/{vip_response.json()['data']['runId']}/debug"
            )
            billing_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"userMessage": "invoice", "intent": "billing"}},
            )
            default_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"userMessage": "hello", "intent": "unknown"}},
            )

        self.assertEqual(vip_response.status_code, 200)
        self.assertEqual(vip_debug_response.status_code, 200)
        self.assertEqual(billing_response.status_code, 200)
        self.assertEqual(default_response.status_code, 200)
        self.assertEqual(vip_response.json()["data"]["output"]["answer"], "API_REAL: GET /text/vip/hello")
        vip_node = next(node for node in vip_debug_response.json()["data"]["nodeDetails"] if node["nodeKey"] == "vip")
        self.assertEqual(vip_node["resourceType"], "API_CALL")
        self.assertGreaterEqual(vip_node["latencyMs"], 0)
        self.assertIn("API_REAL", vip_node["outputSummary"])
        self.assertGreaterEqual(vip_node["totalTokens"], vip_node["outputTokens"])
        self.assertEqual(billing_response.json()["data"]["output"]["answer"], "API_REAL: GET /text/billing/invoice")
        self.assertEqual(default_response.json()["data"]["output"]["answer"], "API_REAL: GET /text/default/hello")

    def test_condition_branch_can_compare_variable_reference_with_default_literal_value(self) -> None:
        with TestClient(app) as client:
            workflow = _create_variable_right_condition_workflow(client)
            matched_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"intent": "vip"}},
            )
            default_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"intent": "billing"}},
            )

        self.assertEqual(matched_response.status_code, 200)
        self.assertEqual(default_response.status_code, 200)
        self.assertEqual(matched_response.json()["data"]["output"]["answer"], "matched")
        self.assertEqual(default_response.json()["data"]["output"]["answer"], "fallback")

    def test_condition_branch_supports_length_and_empty_operators(self) -> None:
        with TestClient(app) as client:
            workflow = _create_length_empty_condition_workflow(client)
            matched_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"message": "hello"}},
            )
            fallback_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"message": "hi", "optional": "filled"}},
            )

        self.assertEqual(matched_response.status_code, 200)
        self.assertEqual(fallback_response.status_code, 200)
        self.assertEqual(matched_response.json()["data"]["output"]["answer"], "matched")
        self.assertEqual(fallback_response.json()["data"]["output"]["answer"], "fallback")


def _create_condition_workflow(client: TestClient, api_base_url: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": "Condition workflow run",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "router",
                    "type": "CONDITION",
                    "name": "Router",
                    "config": {"expression": "{{start.intent}}", "outputVariable": "route"},
                },
                {
                    "nodeKey": "vip",
                    "type": "API_CALL",
                    "name": "VIP",
                    "config": {"method": "GET", "url": f"{api_base_url}/text/vip/{{{{start.userMessage}}}}", "outputVariable": "answer"},
                },
                {
                    "nodeKey": "default",
                    "type": "API_CALL",
                    "name": "Default",
                    "config": {"method": "GET", "url": f"{api_base_url}/text/default/{{{{start.userMessage}}}}", "outputVariable": "answer"},
                },
                {
                    "nodeKey": "billing",
                    "type": "API_CALL",
                    "name": "Billing",
                    "config": {"method": "GET", "url": f"{api_base_url}/text/billing/{{{{start.userMessage}}}}", "outputVariable": "answer"},
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "router", "condition": None},
                {"sourceNodeKey": "router", "targetNodeKey": "default", "condition": None},
                {"sourceNodeKey": "router", "targetNodeKey": "vip", "condition": "vip"},
                {"sourceNodeKey": "router", "targetNodeKey": "billing", "condition": "billing"},
                {"sourceNodeKey": "vip", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "billing", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "default", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    return response.json()["data"]


def _create_variable_right_condition_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": "Condition variable right run",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "router",
                    "type": "CONDITION",
                    "name": "Router",
                    "config": {
                        "outputVariable": "route",
                        "defaultBranch": "fallback",
                        "conditionBranches": [
                            {
                                "key": "matched",
                                "logic": "AND",
                                "conditions": [
                                    {
                                        "left": {"valueMode": "reference", "value": "{{start.intent}}"},
                                        "operator": "equals",
                                        "right": {"valueMode": "literal", "value": "vip"},
                                    }
                                ],
                            }
                        ],
                    },
                },
                {
                    "nodeKey": "matched",
                    "type": "END",
                    "name": "Matched",
                    "config": {"outputVariable": "answer", "output": "matched"},
                },
                {
                    "nodeKey": "fallback",
                    "type": "END",
                    "name": "Fallback",
                    "config": {"outputVariable": "answer", "output": "fallback"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "router", "condition": None},
                {"sourceNodeKey": "router", "targetNodeKey": "matched", "condition": "matched"},
                {"sourceNodeKey": "router", "targetNodeKey": "fallback", "condition": None},
            ],
        },
    )
    return response.json()["data"]


def _create_length_empty_condition_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": "Condition length empty run",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "router",
                    "type": "CONDITION",
                    "name": "Router",
                    "config": {
                        "outputVariable": "route",
                        "defaultBranch": "fallback",
                        "conditionBranches": [
                            {
                                "key": "matched",
                                "logic": "AND",
                                "conditions": [
                                    {
                                        "left": {"valueMode": "reference", "value": "{{start.message}}"},
                                        "operator": "length_greater_or_equal",
                                        "right": {"valueMode": "literal", "value": "5"},
                                    },
                                    {
                                        "left": {"valueMode": "reference", "value": "{{start.optional}}"},
                                        "operator": "is_empty",
                                        "right": {"valueMode": "literal", "value": "ignored"},
                                    },
                                ],
                            }
                        ],
                    },
                },
                {
                    "nodeKey": "matched",
                    "type": "END",
                    "name": "Matched",
                    "config": {"outputVariable": "answer", "output": "matched"},
                },
                {
                    "nodeKey": "fallback",
                    "type": "END",
                    "name": "Fallback",
                    "config": {"outputVariable": "answer", "output": "fallback"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "router", "condition": None},
                {"sourceNodeKey": "router", "targetNodeKey": "matched", "condition": "matched"},
                {"sourceNodeKey": "router", "targetNodeKey": "fallback", "condition": None},
            ],
        },
    )
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
