import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ChatflowConversationRunTest(unittest.TestCase):
    def test_chatflow_run_renders_system_variables(self) -> None:
        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/chatflows",
                json={
                    "name": f"Chatflow conversation {time.time_ns()}",
                    "description": "",
                    "nodes": [
                        {
                            "nodeKey": "start",
                            "type": "START",
                            "name": "Start",
                            "config": {"outputVariables": ["sys.query", "sys.channel"]},
                        },
                        {
                            "nodeKey": "end",
                            "type": "END",
                            "name": "End",
                            "config": {
                                "outputVariable": "output",
                                "output": "收到 {{sys.query}} via {{sys.channel}} for {{global.brand}}/{{global.locale}}",
                            },
                        },
                    ],
                    "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
                },
            )
            chatflow = create_response.json()["data"]
            run_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "userMessage": "查订单",
                        "sys.query": "查订单",
                        "sys.channel": "web",
                        "global.brand": "Hify",
                        "global.locale": "zh-CN",
                    }
                },
            )

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(run_response.status_code, 200)
        data = run_response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"]["output"], "收到 查订单 via web for Hify/zh-CN")


if __name__ == "__main__":
    unittest.main()
