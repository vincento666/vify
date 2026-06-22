import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


class IntentRecognitionNodeIntegrationTest(unittest.TestCase):
    def test_chatflow_intent_recognition_routes_to_matching_branch(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_intent_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"sys.query": "我要申请退款，订单有问题"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["output"], {"final": "refund path"})

    def test_intent_recognition_uses_default_branch_when_no_intent_matches(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_intent_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"sys.query": "今天天气怎么样"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["output"], {"final": "default path"})

    def test_selected_intent_node_run_returns_confidence_and_reason(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_intent_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/nodes/intent_1/runs",
                json={"input": {"sys.query": "查一下物流"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        output = response.json()["data"]["output"]
        self.assertEqual(output["intent"], "shipping")
        self.assertGreaterEqual(output["confidence"], 0.5)
        self.assertIn("matched", output["reason"])


def _create_intent_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Intent Chatflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "intent_1",
                    "type": "INTENT_RECOGNITION",
                    "name": "意图识别",
                    "config": {
                        "inputSource": "{{start.sys.query}}",
                        "outputVariable": "intent",
                        "defaultIntent": "default",
                        "classifierMode": "fake",
                        "intents": [
                            {
                                "key": "refund",
                                "name": "退款",
                                "description": "用户要退款或售后",
                                "examples": ["退款", "退货", "售后"],
                            },
                            {
                                "key": "shipping",
                                "name": "物流",
                                "description": "用户查询物流、快递或配送",
                                "examples": ["物流", "快递", "配送"],
                            },
                        ],
                    },
                },
                {"nodeKey": "refund_end", "type": "END", "name": "Refund", "config": {"outputVariable": "final", "output": "refund path"}},
                {"nodeKey": "shipping_end", "type": "END", "name": "Shipping", "config": {"outputVariable": "final", "output": "shipping path"}},
                {"nodeKey": "default_end", "type": "END", "name": "Default", "config": {"outputVariable": "final", "output": "default path"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "intent_1", "condition": None},
                {"sourceNodeKey": "intent_1", "targetNodeKey": "refund_end", "condition": "refund"},
                {"sourceNodeKey": "intent_1", "targetNodeKey": "shipping_end", "condition": "shipping"},
                {"sourceNodeKey": "intent_1", "targetNodeKey": "default_end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
