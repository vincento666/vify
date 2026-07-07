import time
import unittest
from datetime import datetime

import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory
from app.main import app


class RuntimeV2LongRunLifecycleEvidenceTest(unittest.TestCase):
    def test_reconnect_query_resume_and_cancel_preserve_events_and_checkpoints(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client, stamp)
            started = _start_runtime_v2_run(client, int(chatflow["id"]), f"resume-{stamp}")
            interrupted = _wait_for_status(client, started["resultRef"], "INTERRUPTED")
            resume_run_id = int(started["runId"])
            resume_checkpoint_id = int(interrupted["checkpoint"]["id"])

        with TestClient(app) as reconnect:
            queried = reconnect.get(f"/api/v1/runtime-runs/{resume_run_id}")
            self.assertEqual(queried.status_code, 200, queried.text)
            queried_data = queried.json()["data"]
            self.assertEqual(queried_data["status"], "INTERRUPTED")
            self.assertEqual(queried_data["checkpoint"]["id"], resume_checkpoint_id)

            replayed_events = reconnect.get(f"/api/v1/runtime-runs/{resume_run_id}/events")
            self.assertEqual(replayed_events.status_code, 200, replayed_events.text)
            events_before_resume = replayed_events.json()["data"]["list"]
            waiting_event = _event(events_before_resume, "workflow_node_waiting")
            self.assertEqual(waiting_event["checkpointId"], resume_checkpoint_id)

            after_waiting = reconnect.get(
                f"/api/v1/runtime-runs/{resume_run_id}/events",
                params={"afterSequence": waiting_event["sequence"]},
            )
            self.assertEqual(after_waiting.status_code, 200, after_waiting.text)
            after_waiting_events = after_waiting.json()["data"]["list"]
            self.assertTrue(after_waiting_events)
            self.assertTrue(
                all(int(event["sequence"]) > int(waiting_event["sequence"]) for event in after_waiting_events)
            )
            self.assertIn("workflow_run_interrupted", [event["type"] for event in after_waiting_events])

            resumed = reconnect.post(
                f"/api/v1/runtime-runs/{resume_run_id}/resume",
                json={"resumeData": {"answer": "yes"}, "idempotencyKey": f"resume-{stamp}"},
            )
            self.assertEqual(resumed.status_code, 200, resumed.text)
            resumed_data = resumed.json()["data"]
            self.assertEqual(resumed_data["status"], "SUCCEEDED")
            self.assertEqual(resumed_data["checkpoint"], None)
            self.assertEqual(resumed_data["output"], {"final": "answer=yes"})

            events_after_resume = reconnect.get(f"/api/v1/runtime-runs/{resume_run_id}/events").json()["data"]["list"]
            resume_event = _event(events_after_resume, "workflow_run_resumed")
            self.assertEqual(resume_event["checkpointId"], resume_checkpoint_id)
            self.assertEqual(_event(events_after_resume, "workflow_run_completed")["checkpointId"], None)

        self.assertEqual(_checkpoint_status(resume_checkpoint_id), "completed")

        with TestClient(app) as client:
            cancel_started = _start_runtime_v2_run(client, int(chatflow["id"]), f"cancel-{stamp}")
            cancel_interrupted = _wait_for_status(client, cancel_started["resultRef"], "INTERRUPTED")
            cancel_run_id = int(cancel_started["runId"])
            cancel_checkpoint_id = int(cancel_interrupted["checkpoint"]["id"])

        with TestClient(app) as reconnect:
            queried = reconnect.get(f"/api/v1/runtime-runs/{cancel_run_id}")
            self.assertEqual(queried.status_code, 200, queried.text)
            self.assertEqual(queried.json()["data"]["checkpoint"]["id"], cancel_checkpoint_id)

            cancelled = reconnect.post(f"/api/v1/runtime-runs/{cancel_run_id}/cancel")
            self.assertEqual(cancelled.status_code, 200, cancelled.text)
            cancelled_data = cancelled.json()["data"]
            self.assertEqual(cancelled_data["status"], "CANCELLED")
            self.assertEqual(cancelled_data["checkpoint"], None)
            self.assertEqual(cancelled_data["cancellation"]["previousStatus"], "INTERRUPTED")

            terminal = reconnect.get(f"/api/v1/runtime-runs/{cancel_run_id}").json()["data"]
            self.assertEqual(terminal["status"], "CANCELLED")
            self.assertEqual(terminal["checkpoint"], None)

            cancel_events = reconnect.get(f"/api/v1/runtime-runs/{cancel_run_id}/events").json()["data"]["list"]
            cancel_event = _event(cancel_events, "workflow_run_cancelled")
            self.assertEqual(cancel_event["checkpointId"], cancel_checkpoint_id)
            self.assertNotIn("workflow_run_completed", [event["type"] for event in cancel_events])

        self.assertEqual(_checkpoint_status(cancel_checkpoint_id), "completed")


def _create_question_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Long-Run Lifecycle {datetime.now().timestamp()}-{stamp}",
            "description": "114.1 runtime v2 lifecycle fixture",
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


def _start_runtime_v2_run(client: TestClient, chatflow_id: int, session_suffix: str) -> dict[str, object]:
    response = client.post(
        f"/api/v1/chatflows/{chatflow_id}/runs",
        json={
            "input": {
                "sys.query": "start",
                "sys.session_id": f"runtime-v2-114-{session_suffix}",
                "sys.conversation_id": f"runtime-v2-114-{session_suffix}",
                "sys.user_id": "runtime-v2-114",
                "sys.channel": "api",
            }
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _wait_for_status(client: TestClient, result_ref: str, wanted_status: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(result_ref)
        assert response.status_code == 200, response.text
        latest = response.json()["data"]
        if latest["status"] == wanted_status:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {wanted_status}; latest={latest}")


def _event(events: list[dict[str, object]], event_type: str) -> dict[str, object]:
    for event in events:
        if event["type"] == event_type:
            return event
    raise AssertionError(f"Missing {event_type}; events={events}")


def _checkpoint_status(checkpoint_id: int) -> str:
    checkpoint_table = Base.metadata.tables["chatflow_checkpoint"]
    with get_session_factory()() as session:
        status = session.execute(
            sa.select(checkpoint_table.c.status).where(checkpoint_table.c.id == checkpoint_id)
        ).scalar_one()
    return str(status)


if __name__ == "__main__":
    unittest.main()
