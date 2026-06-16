import json
import time
import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


class ChatflowRuntimeV2SpikeTest(unittest.TestCase):
    def test_runs_v2_returns_refs_and_streams_l1_events_before_terminal_result(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client)

            started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"sys.query": "Ada"}},
            )

            self.assertEqual(started.status_code, 200, started.text)
            data = started.json()["data"]
            self.assertEqual(data["status"], "RUNNING")
            self.assertEqual(data["transport"]["decision"], "sse")
            self.assertIn("/api/v1/runtime-runs/", data["eventStreamRef"])
            with client.stream("GET", f"{data['eventStreamRef']}&_testLimit=1") as stream:
                first = _read_sse_events(stream, 1)[0]

            self.assertEqual(first["type"], "workflow_run_started")
            self.assertEqual(first["level"], "L1")
            self.assertEqual(first["source"], "chatflow_runtime_v2")
            self.assertEqual(client.get(data["resultRef"]).json()["data"]["status"], "RUNNING")

            terminal = _wait_for_result(client, data["resultRef"])
            self.assertEqual(terminal["status"], "SUCCEEDED")
            self.assertEqual(terminal["output"], {"final": "sent: Hello Ada"})
            events = client.get(data["eventsRef"]).json()["data"]["list"]
            self.assertIn("workflow_node_started", [event["type"] for event in events])
            self.assertIn("workflow_run_completed", [event["type"] for event in events])

    def test_question_path_interrupts_then_runtime_v2_resume_completes_same_run(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client)
            started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"sys.query": "start"}},
            )

            data = started.json()["data"]
            interrupted = _wait_for_result(client, data["resultRef"], wanted_status="INTERRUPTED")
            resume = client.post(
                f"/api/v1/runtime-runs/{data['runId']}/resume",
                json={"resumeData": {"answer": "yes"}},
            )
            terminal = client.get(data["resultRef"])

        self.assertEqual(started.status_code, 200, started.text)
        self.assertEqual(interrupted["status"], "INTERRUPTED")
        self.assertEqual(interrupted["checkpoint"]["pendingNodeKey"], "question_1")
        self.assertEqual(resume.status_code, 200, resume.text)
        self.assertEqual(resume.json()["data"]["status"], "SUCCEEDED")
        self.assertEqual(terminal.json()["data"]["output"], {"final": "answer=yes"})

    def test_legacy_chatflow_sse_replay_stays_separate_from_runtime_v2_live_events(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client)
            with client.stream(
                "POST",
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                headers={"Accept": "text/event-stream"},
                json={"input": {"sys.query": "Ada"}},
            ) as stream:
                legacy_events = _read_legacy_sse(stream)

        self.assertIn("run_done", [event["type"] for event in legacy_events])
        self.assertNotIn("workflow_run_started", [event["type"] for event in legacy_events])


def _wait_for_result(
    client: TestClient,
    result_ref: str,
    wanted_status: str = "SUCCEEDED",
    timeout: float = 5.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(result_ref)
        latest = response.json()["data"]
        if latest["status"] == wanted_status:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {wanted_status}; latest={latest}")


def _read_sse_events(response, count: int) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in response.iter_lines():
        if line.startswith("data: "):
            events.append(json.loads(line.removeprefix("data: ")))
            if len(events) >= count:
                return events
    return events


def _read_legacy_sse(response) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in response.iter_lines():
        if line.startswith("data: "):
            events.append(json.loads(line.removeprefix("data: ")))
    return events


def _create_message_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Message {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "message_1",
                    "type": "MESSAGE",
                    "name": "Message",
                    "config": {
                        "content": "Hello {{start.sys.query}}",
                        "outputVariable": "content",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "sent: {{message_1.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "message_1", "condition": None},
                {"sourceNodeKey": "message_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_question_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Question {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "question_1",
                    "type": "QUESTION",
                    "name": "Question",
                    "config": {"question": "Continue?", "outputVariable": "answer", "answerType": "text"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "answer={{question_1.answer}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
                {"sourceNodeKey": "question_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
