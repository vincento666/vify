import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class WorkflowRunDebugDetailTest(unittest.TestCase):
    def test_workflow_run_debug_detail_is_scoped_to_owning_canvas(self) -> None:
        with TestClient(app) as client:
            workflow = client.post(
                "/api/v1/workflows",
                json={
                    "name": f"021.2 Debug Detail {time.time_ns()}",
                    "description": "",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "开始", "config": {}},
                        {
                            "nodeKey": "end",
                            "type": "END",
                            "name": "结束",
                            "config": {"outputVariable": "answer", "output": "echo {{start.USER_INPUT}}"},
                        },
                    ],
                    "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
                },
            ).json()["data"]
            run = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"USER_INPUT": "embedded debug"}},
            ).json()["data"]

            response = client.get(f"/api/v1/workflows/{workflow['id']}/runs/{run['runId']}/debug")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["runId"], run["runId"])
        self.assertEqual(data["ownerType"], "WORKFLOW")
        self.assertEqual(data["ownerId"], workflow["id"])
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"]["answer"], "echo embedded debug")
        self.assertGreaterEqual(len(data["callTree"]), 2)
        self.assertGreaterEqual(len(data["flamegraph"]), 2)
        self.assertTrue(any(node["nodeKey"] == "start" for node in data["nodeDetails"]))
        self.assertTrue(any(node["nodeKey"] == "end" for node in data["nodeDetails"]))
        end_node = next(node for node in data["nodeDetails"] if node["nodeKey"] == "end")
        self.assertIn("inputs", end_node)
        self.assertIn("embedded debug", str(end_node["inputs"]))
        self.assertGreaterEqual(end_node["latencyMs"], 0)
        self.assertIn("embedded debug", end_node["outputSummary"])
        self.assertEqual(end_node["errorSummary"], "")
        self.assertEqual(end_node["resourceType"], "END")
        self.assertIsNone(end_node["costEstimate"])
        self.assertTrue(end_node["usageEstimated"])
        self.assertGreaterEqual(end_node["outputTokens"], 1)
        self.assertEqual(end_node["totalTokens"], end_node["inputTokens"] + end_node["outputTokens"])
        self.assertIn("events", end_node)


if __name__ == "__main__":
    unittest.main()
