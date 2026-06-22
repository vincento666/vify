import json
import time

from fastapi.testclient import TestClient

from app.main import app


def test_chatflow_run_accepts_sse_and_streams_node_events() -> None:
    with TestClient(app) as client:
        create_response = client.post(
            "/api/v1/chatflows",
            json={
                "name": f"Chatflow SSE stream {time.time_ns()}",
                "description": "",
                "nodes": [
                    {
                        "nodeKey": "start",
                        "type": "START",
                        "name": "Start",
                        "config": {"outputVariables": ["sys.query"]},
                    },
                    {
                        "nodeKey": "message_1",
                        "type": "MESSAGE",
                        "name": "Message",
                        "config": {
                            "content": "hello {{start.sys.query}}",
                            "outputVariable": "content",
                            "streamOutput": "enabled",
                        },
                    },
                    {
                        "nodeKey": "end",
                        "type": "END",
                        "name": "End",
                        "config": {"outputVariable": "final", "output": "Final {{message_1.content}}"},
                    },
                ],
                "edges": [
                    {"sourceNodeKey": "start", "targetNodeKey": "message_1", "condition": None},
                    {"sourceNodeKey": "message_1", "targetNodeKey": "end", "condition": None},
                ],
            },
        )
        chatflow_id = create_response.json()["data"]["id"]
        run_response = client.post(
            f"/api/v1/chatflows/{chatflow_id}/runs-legacy",
            headers={"Accept": "text/event-stream"},
            json={"input": {"sys.query": "stream"}},
        )

    assert run_response.status_code == 200
    assert run_response.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse_events(run_response.text)
    assert [(event["type"], event.get("nodeKey"), event.get("content")) for event in events[:-1]] == [
        ("message_delta", "message_1", "hello stream"),
        ("message_done", "message_1", "hello stream"),
        ("message_delta", "end", "Final hello stream"),
        ("message_done", "end", "Final hello stream"),
    ]
    assert events[-1]["type"] == "run_done"
    assert events[-1]["status"] == "SUCCEEDED"
    assert events[-1]["output"] == {"final": "Final hello stream"}


def _parse_sse_events(body: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for block in body.strip().split("\n\n"):
        if block.startswith("data:"):
            events.append(json.loads(block.removeprefix("data:").strip()))
    return events
