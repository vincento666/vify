import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ChatflowVariableRoundtripTest(unittest.TestCase):
    def test_chatflow_template_variables_round_trip_in_node_config(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chatflows",
                json={
                    "name": f"Chatflow variable {time.time_ns()}",
                    "description": "",
                    "nodes": [
                        {
                            "nodeKey": "start",
                            "type": "START",
                            "name": "Start",
                            "config": {"outputVariables": ["sys.query", "sys.conversation_id"]},
                        },
                        {
                            "nodeKey": "end",
                            "type": "END",
                            "name": "End",
                            "config": {"outputVariable": "output", "output": "收到 {{sys.query}}"},
                        },
                    ],
                    "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
                },
            )
            created = response.json()["data"]
            detail_response = client.get(f"/api/v1/chatflows/{created['id']}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()["data"]
        end_node = next(node for node in detail["nodes"] if node["nodeKey"] == "end")
        self.assertEqual(end_node["config"]["output"], "收到 {{sys.query}}")

    def test_end_output_parameter_reference_mapping_runs_through_chatflow(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chatflows",
                json={
                    "name": f"Chatflow end mapping {time.time_ns()}",
                    "description": "",
                    "nodes": [
                        {
                            "nodeKey": "start",
                            "type": "START",
                            "name": "Start",
                            "config": {"outputVariables": ["sys.query"]},
                        },
                        {
                            "nodeKey": "end",
                            "type": "END",
                            "name": "End",
                            "config": {
                                "outputVariable": "output",
                                "output": "收到 {{output}}",
                                "outputParameters": [
                                    {
                                        "name": "output",
                                        "type": "string",
                                        "valueMode": "reference",
                                        "value": "{{start.sys.query}}",
                                    }
                                ],
                            },
                        },
                    ],
                    "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
                },
            )
            chatflow = response.json()["data"]
            run_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"userMessage": "查订单", "sys.query": "查订单"}},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(run_response.status_code, 200)
        data = run_response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"output": "收到 查订单"})


if __name__ == "__main__":
    unittest.main()
