import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ObserveSurfacesTest(unittest.TestCase):
    def test_observe_lists_runs_sessions_handoffs_and_metrics(self) -> None:
        with TestClient(app) as client:
            chatflow = client.post(
                "/api/v1/chatflows",
                json={
                    "name": f"Observe Chatflow {time.time_ns()}",
                    "description": "",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                        {
                            "nodeKey": "handoff_1",
                            "type": "TRANSFER_TO_HUMAN",
                            "name": "Handoff",
                            "config": {"queue": "observe-support", "message": "转人工"},
                        },
                        {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final"}},
                    ],
                    "edges": [
                        {"sourceNodeKey": "start", "targetNodeKey": "handoff_1", "condition": None},
                        {"sourceNodeKey": "handoff_1", "targetNodeKey": "end", "condition": None},
                    ],
                },
            ).json()["data"]
            run = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={
                    "input": {
                        "sys.query": "need human",
                        "sys.conversation_id": f"observe-{time.time_ns()}",
                        "sys.user_id": "observe-user",
                        "sys.channel": "web",
                    }
                },
            ).json()["data"]

            runs_response = client.get("/api/v1/observe/runs", params={"flowType": "CHATFLOW", "pageSize": 50})
            detail_response = client.get(f"/api/v1/observe/runs/{run['runId']}")
            sessions_response = client.get("/api/v1/observe/sessions", params={"pageSize": 50})
            metrics_response = client.get("/api/v1/observe/metrics")

        self.assertEqual(runs_response.status_code, 200)
        runs = runs_response.json()["data"]["list"]
        observed_run = next(item for item in runs if item["runId"] == run["runId"])
        self.assertEqual(observed_run["status"], "INTERRUPTED")
        self.assertEqual(observed_run["flowType"], "CHATFLOW")
        self.assertEqual(observed_run["channel"], "web")
        self.assertEqual(observed_run["userId"], "observe-user")

        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()["data"]
        self.assertEqual(detail["runId"], run["runId"])
        self.assertTrue(any(node["nodeKey"] == "handoff_1" for node in detail["nodeRuns"]))
        self.assertTrue(any(event["type"] == "handoff_requested" for event in detail["events"]))

        sessions = sessions_response.json()["data"]["list"]
        self.assertTrue(any(item["currentRunId"] == run["runId"] and item["status"] == "handoff" for item in sessions))

        metrics = metrics_response.json()["data"]
        self.assertGreaterEqual(metrics["runCount"], 1)
        self.assertGreaterEqual(metrics["handoffCount"], 1)
        self.assertIn("web", metrics["channelDistribution"])


if __name__ == "__main__":
    unittest.main()
