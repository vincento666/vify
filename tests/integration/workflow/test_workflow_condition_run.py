import unittest

from fastapi.testclient import TestClient

from app.main import app


class WorkflowConditionRunTest(unittest.TestCase):
    def test_condition_node_selects_matching_branch_or_default_branch(self) -> None:
        with TestClient(app) as client:
            workflow = _create_condition_workflow(client)

            vip_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"userMessage": "hello", "intent": "vip"}},
            )
            default_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"userMessage": "hello", "intent": "unknown"}},
            )

        self.assertEqual(vip_response.status_code, 200)
        self.assertEqual(default_response.status_code, 200)
        self.assertEqual(vip_response.json()["data"]["output"]["answer"], "LLM mock: VIP hello")
        self.assertEqual(default_response.json()["data"]["output"]["answer"], "LLM mock: Default hello")


def _create_condition_workflow(client: TestClient) -> dict[str, object]:
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
                    "type": "LLM",
                    "name": "VIP",
                    "config": {"prompt": "VIP {{start.userMessage}}", "outputVariable": "answer"},
                },
                {
                    "nodeKey": "default",
                    "type": "LLM",
                    "name": "Default",
                    "config": {"prompt": "Default {{start.userMessage}}", "outputVariable": "answer"},
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "router", "condition": None},
                {"sourceNodeKey": "router", "targetNodeKey": "default", "condition": None},
                {"sourceNodeKey": "router", "targetNodeKey": "vip", "condition": "vip"},
                {"sourceNodeKey": "vip", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "default", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
