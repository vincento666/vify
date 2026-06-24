import json
import time

from fastapi.testclient import TestClient

from app.main import app


def test_chatflow_runs_stream_covers_success_failure_waiting_and_reconnect() -> None:
    with TestClient(app) as client:
        success = _create_chatflow(
            client,
            "Chatflow Runs Stream E2E Success",
            nodes=[
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "message_1",
                    "type": "MESSAGE",
                    "name": "Message",
                    "config": {"content": "hello {{start.sys.query}}", "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{message_1.content}}"},
                },
            ],
            edges=[
                {"sourceNodeKey": "start", "targetNodeKey": "message_1", "condition": None},
                {"sourceNodeKey": "message_1", "targetNodeKey": "end", "condition": None},
            ],
        )
        success_first = _start_stream(client, int(success["id"]), {"sys.query": "Ada"})
        success_result = _wait_for_status(client, int(success_first["runId"]), "SUCCEEDED")
        success_replay = _stream_events(
            client,
            int(success_first["runId"]),
            after_sequence=int(success_first["sequence"]) - 1,
            limit=1,
        )[0]

        failing = _create_chatflow(
            client,
            "Chatflow Runs Stream E2E Failure",
            nodes=[
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
            edges=[
                {"sourceNodeKey": "start", "targetNodeKey": "code_1", "condition": None},
                {"sourceNodeKey": "code_1", "targetNodeKey": "end", "condition": None},
            ],
        )
        failure_first = _start_stream(client, int(failing["id"]), {"sys.query": "fail"})
        failure_result = _wait_for_status(client, int(failure_first["runId"]), "FAILED")
        failure_events = _list_events(client, int(failure_first["runId"]))

        waiting = _create_chatflow(
            client,
            "Chatflow Runs Stream E2E Waiting",
            nodes=[
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
            edges=[
                {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
                {"sourceNodeKey": "question_1", "targetNodeKey": "end", "condition": None},
            ],
        )
        waiting_first = _start_stream(client, int(waiting["id"]), {"sys.query": "wait"})
        waiting_result = _wait_for_status(client, int(waiting_first["runId"]), "INTERRUPTED")
        waiting_events = _list_events(client, int(waiting_first["runId"]))
        waiting_event = next(event for event in waiting_events if event["type"] == "workflow_node_waiting")
        after_waiting = _stream_events(
            client,
            int(waiting_first["runId"]),
            after_sequence=int(waiting_event["sequence"]),
            limit=1,
        )[0]
        resumed = client.post(
            f"/api/v1/runtime-runs/{waiting_first['runId']}/resume",
            json={"resumeData": {"answer": "yes"}},
        )

    assert success_first["type"] == "workflow_run_started"
    assert success_result["output"] == {"final": "hello Ada"}
    assert success_replay["runId"] == success_first["runId"]
    assert failure_result["status"] == "FAILED"
    assert "workflow_run_failed" in [event["type"] for event in failure_events]
    assert waiting_result["checkpoint"]["pendingNodeKey"] == "question_1"
    assert int(after_waiting["sequence"]) > int(waiting_event["sequence"])
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["data"]["status"] == "SUCCEEDED"


def _create_chatflow(
    client: TestClient,
    name: str,
    *,
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"{name} {time.time_ns()}",
            "description": "chatflow runs stream e2e fixture",
            "nodes": nodes,
            "edges": edges,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _start_stream(client: TestClient, chatflow_id: int, input_data: dict[str, object]) -> dict[str, object]:
    with client.stream(
        "POST",
        f"/api/v1/chatflows/{chatflow_id}/runs:stream?_testLimit=1",
        json={"input": input_data, "idempotencyKey": f"e2e-runs-stream-{time.time_ns()}"},
    ) as stream:
        assert stream.headers.get("content-type", "").startswith("text/event-stream")
        return _read_sse_event(stream)


def _stream_events(
    client: TestClient,
    run_id: int,
    *,
    after_sequence: int,
    limit: int,
) -> list[dict[str, object]]:
    response = client.get(
        f"/api/v1/runtime-runs/{run_id}/events/stream",
        params={"afterSequence": after_sequence, "_testLimit": limit},
    )
    assert response.status_code == 200, response.text
    return _parse_sse_events(response.text)


def _list_events(client: TestClient, run_id: int) -> list[dict[str, object]]:
    response = client.get(f"/api/v1/runtime-runs/{run_id}/events")
    assert response.status_code == 200, response.text
    return response.json()["data"]["list"]


def _wait_for_status(
    client: TestClient,
    run_id: int,
    wanted_status: str,
    timeout: float = 5.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/runtime-runs/{run_id}/result")
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
    return [
        json.loads(block.removeprefix("data:").strip())
        for block in body.strip().split("\n\n")
        if block.startswith("data:")
    ]
