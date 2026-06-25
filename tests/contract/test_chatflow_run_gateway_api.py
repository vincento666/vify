import json
import time
import unittest
from unittest.mock import patch

import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory
from app.main import app
from app.modules.workflow.domain.runtime_invocation_gateway import RuntimeInvocationGateway
from app.modules.workflow.domain.runtime_v2 import ChatflowRuntimeV2Service
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.publish_repository import WorkflowPublishRepository
from app.modules.workflow.infra.repository import WorkflowRepository


class ChatflowRunGatewayApiTest(unittest.TestCase):
    def test_chatflow_runs_endpoint_is_runtime_v2_gateway_with_durable_job(self) -> None:
        with TestClient(app) as client, patch("app.modules.workflow.web.router.threading.Thread"):
            chatflow = _create_chatflow(client)
            version = client.post(f"/api/v1/chatflows/{chatflow['id']}/publish").json()["data"]
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {"sys.query": "gateway"},
                    "versionId": version["id"],
                    "idempotencyKey": f"chatflow-run-gateway-{time.time_ns()}",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        run_id = int(data["runId"])
        self.assertEqual(data["runtimeVersion"], 2)
        self.assertEqual(data["ownerType"], "CHATFLOW")
        self.assertEqual(data["ownerId"], chatflow["id"])
        self.assertEqual(data["chatflowId"], chatflow["id"])
        self.assertEqual(data["versionId"], version["id"])
        self.assertNotIn("output", data)
        self.assertEqual(data["status"], "RUNNING")
        self.assertEqual(data["statusRef"], f"/api/v1/runtime-runs/{run_id}")
        self.assertEqual(data["eventsRef"], f"/api/v1/runtime-runs/{run_id}/events")
        self.assertEqual(data["nodesRef"], f"/api/v1/runtime-runs/{run_id}/nodes")
        self.assertEqual(data["resultRef"], f"/api/v1/runtime-runs/{run_id}/result")
        self.assertEqual(
            data["runtimeRefs"],
            {
                "runId": run_id,
                "statusRef": data["statusRef"],
                "eventsRef": data["eventsRef"],
                "eventStreamRef": data["eventStreamRef"],
                "nodesRef": data["nodesRef"],
                "resultRef": data["resultRef"],
            },
        )
        job = _runtime_job_for_run(run_id)
        self.assertEqual(job["owner_type"], "CHATFLOW")
        self.assertEqual(job["owner_id"], chatflow["id"])
        self.assertEqual(job["job_type"], "runtime_v2_completion")
        self.assertEqual(job["status"], "QUEUED")

    def test_chatflow_runs_stream_starts_runtime_v2_run_and_streams_same_run_events(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(client)
            with client.stream(
                "POST",
                f"/api/v1/chatflows/{chatflow['id']}/runs:stream?_testLimit=1",
                json={
                    "input": {"sys.query": "stream"},
                    "idempotencyKey": f"chatflow-run-stream-{time.time_ns()}",
                },
            ) as stream:
                content_type = stream.headers.get("content-type", "")
                event = _read_sse_event(stream)

            run_id = int(event["runId"])
            replay = client.get(f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0&_testLimit=1")
            replay_event = _parse_sse_events(replay.text)[0]

        self.assertTrue(content_type.startswith("text/event-stream"))
        self.assertEqual(event["type"], "workflow_run_started")
        self.assertEqual(event["payload"]["ownerType"], "CHATFLOW")
        self.assertEqual(event["payload"]["ownerId"], chatflow["id"])
        self.assertEqual(replay_event["runId"], run_id)
        self.assertEqual(replay_event["sequence"], event["sequence"])

    def test_chatflow_runs_stream_exposes_failure_events_through_runtime_reconnect(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_failing_chatflow(client)
            with client.stream(
                "POST",
                f"/api/v1/chatflows/{chatflow['id']}/runs:stream?_testLimit=1",
                json={
                    "input": {"sys.query": "fail"},
                    "idempotencyKey": f"chatflow-run-stream-fail-{time.time_ns()}",
                },
            ) as stream:
                first = _read_sse_event(stream)

            run_id = int(first["runId"])
            terminal = _wait_for_result(client, f"/api/v1/runtime-runs/{run_id}/result", wanted_status="FAILED")
            events = client.get(f"/api/v1/runtime-runs/{run_id}/events").json()["data"]["list"]

        self.assertEqual(terminal["status"], "FAILED")
        self.assertIn("workflow_run_failed", [event["type"] for event in events])
        self.assertEqual(events[0]["runId"], run_id)

    def test_chatflow_runs_stream_waiting_input_can_resume_from_runtime_event_cursor(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client)
            with client.stream(
                "POST",
                f"/api/v1/chatflows/{chatflow['id']}/runs:stream?_testLimit=1",
                json={
                    "input": {"sys.query": "wait"},
                    "idempotencyKey": f"chatflow-run-stream-wait-{time.time_ns()}",
                },
            ) as stream:
                first = _read_sse_event(stream)

            run_id = int(first["runId"])
            interrupted = _wait_for_result(
                client,
                f"/api/v1/runtime-runs/{run_id}/result",
                wanted_status="INTERRUPTED",
            )
            events = client.get(f"/api/v1/runtime-runs/{run_id}/events").json()["data"]["list"]
            waiting_event = next(event for event in events if event["type"] == "workflow_node_waiting")
            reconnect = client.get(
                f"/api/v1/runtime-runs/{run_id}/events/stream"
                f"?afterSequence={waiting_event['sequence']}&_testLimit=1"
            )
            resumed = client.post(
                f"/api/v1/runtime-runs/{run_id}/resume",
                json={"resumeData": {"answer": "yes"}},
            )

        self.assertEqual(interrupted["status"], "INTERRUPTED")
        self.assertEqual(interrupted["checkpoint"]["pendingNodeKey"], "question_1")
        reconnect_event = _parse_sse_events(reconnect.text)[0]
        self.assertGreater(int(reconnect_event["sequence"]), int(waiting_event["sequence"]))
        self.assertEqual(resumed.status_code, 200, resumed.text)
        self.assertEqual(resumed.json()["data"]["status"], "SUCCEEDED")

    def test_chatflow_runs_stream_sends_idle_heartbeat(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(client)
            with client.stream(
                "POST",
                f"/api/v1/chatflows/{chatflow['id']}/runs:stream"
                "?afterSequence=999999&heartbeatMs=100&_testHeartbeatLimit=1",
                json={
                    "input": {"sys.query": "heartbeat"},
                    "idempotencyKey": f"chatflow-run-stream-heartbeat-{time.time_ns()}",
                },
            ) as stream:
                content_type = stream.headers.get("content-type", "")
                first_line = next(stream.iter_lines())

        self.assertTrue(content_type.startswith("text/event-stream"))
        self.assertEqual(first_line, ": heartbeat")

    def test_internal_gateway_events_match_runtime_replay_and_sse_sequence(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(client)
            with get_session_factory()() as session:
                gateway = RuntimeInvocationGateway(
                    ChatflowRuntimeV2Service(
                        WorkflowRepository(session),
                        ChatflowStateRepository(session),
                        publish_repository=WorkflowPublishRepository(session),
                        completion_delay_seconds=0.0,
                    )
                )
                internal = gateway.start_and_wait(
                    owner_id=int(chatflow["id"]),
                    input_data={"sys.query": "internal-vs-external"},
                    idempotency_key=f"chatflow-internal-events-{time.time_ns()}",
                )

            run_id = int(internal["runId"])
            internal_events = internal["events"]["list"]
            replay_events = client.get(f"/api/v1/runtime-runs/{run_id}/events").json()["data"]["list"]
            sse_events = _parse_sse_events(
                client.get(
                    f"/api/v1/runtime-runs/{run_id}/events/stream"
                    f"?afterSequence=0&_testLimit={len(internal_events)}"
                ).text
            )

        self.assertGreaterEqual(len(internal_events), 2)
        self.assertEqual(
            [(event["sequence"], event["type"], event["runId"]) for event in replay_events],
            [(event["sequence"], event["type"], event["runId"]) for event in internal_events],
        )
        self.assertEqual(
            [(event["sequence"], event["type"], event["runId"]) for event in sse_events],
            [(event["sequence"], event["type"], event["runId"]) for event in internal_events],
        )

    def test_chatflow_runs_legacy_keeps_sync_compatibility(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"sys.query": "legacy"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "gateway message"})
        self.assertIn("debugUrl", data)


def _runtime_job_for_run(run_id: int) -> dict[str, object]:
    job_table = Base.metadata.tables["runtime_jobs"]
    with get_session_factory()() as session:
        row = (
            session.execute(
                sa.select(job_table)
                .where(job_table.c.run_id == run_id, job_table.c.deleted.is_(False))
                .order_by(job_table.c.id.desc())
            )
            .mappings()
            .first()
        )
    if row is None:
        raise AssertionError(f"No runtime job found for run {run_id}")
    return dict(row)


def _wait_for_result(
    client: TestClient,
    result_ref: str,
    *,
    wanted_status: str,
    timeout: float = 5.0,
) -> dict[str, object]:
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


def _read_sse_event(stream) -> dict[str, object]:
    data: list[str] = []
    for line in stream.iter_lines():
        if line.startswith("data:"):
            data.append(line[len("data:") :].strip())
        if data and not line:
            return json.loads("\n".join(data))
    if data:
        return json.loads("\n".join(data))
    raise AssertionError("No SSE data frame returned")


def _parse_sse_events(body: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for block in body.strip().split("\n\n"):
        if block.startswith("data:"):
            events.append(json.loads(block.removeprefix("data:").strip()))
    return events


def _create_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Chatflow Run Gateway {time.time_ns()}",
            "description": "chatflow default run gateway contract fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "message_1",
                    "type": "MESSAGE",
                    "name": "Message",
                    "config": {"content": "gateway message", "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{message_1.content}}"},
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


def _create_failing_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Chatflow Run Stream Failure {time.time_ns()}",
            "description": "chatflow stream failure fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "code_1",
                    "type": "CODE",
                    "name": "Failing Code",
                    "config": {"language": "python", "code": "result = 1 / 0"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{code_1.result}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "code_1", "condition": None},
                {"sourceNodeKey": "code_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_question_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Chatflow Run Stream Waiting {time.time_ns()}",
            "description": "chatflow stream waiting-input fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "question_1",
                    "type": "QUESTION",
                    "name": "Question",
                    "config": {
                        "question": "Continue?",
                        "outputVariable": "answer",
                        "answerType": "text",
                    },
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
