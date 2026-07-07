import time
import unittest
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


class ChatflowFinalOutputRulesTest(unittest.TestCase):
    def test_end_output_takes_priority_over_prior_reply_candidate(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(
                client,
                nodes=[
                    _node("start", "START"),
                    _node(
                        "candidate",
                        "CODE",
                        {
                            "code": 'result = {"answer": "priority candidate", "replyPriority": 99}',
                        },
                    ),
                    _node("end", "END", {"outputVariable": "final", "output": "end wins"}),
                ],
                edges=[_edge("start", "candidate"), _edge("candidate", "end")],
            )
            started = _start_chatflow(client, chatflow["id"])
            terminal = _wait_for_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "end wins"})
        self.assertEqual(_assistant_messages(events), ["end wins"])

    def test_answer_mapping_is_used_when_end_has_no_visible_output(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(
                client,
                nodes=[
                    _node("start", "START"),
                    _node(
                        "message_1",
                        "MESSAGE",
                        {"content": "mapped answer", "outputVariable": "answer"},
                    ),
                    _node("end", "END", {"outputVariable": "unused"}),
                ],
                edges=[_edge("start", "message_1"), _edge("message_1", "end")],
            )
            started = _start_chatflow(client, chatflow["id"])
            terminal = _wait_for_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"answer": "mapped answer"})
        self.assertEqual(_assistant_messages(events), ["mapped answer"])

    def test_priority_reply_node_wins_over_lower_priority_candidates(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(
                client,
                nodes=[
                    _node("start", "START"),
                    _node(
                        "low_reply",
                        "CODE",
                        {
                            "code": 'result = {"answer": "low priority reply", "replyPriority": 10}',
                        },
                    ),
                    _node(
                        "high_reply",
                        "CODE",
                        {
                            "code": 'result = {"answer": "high priority reply", "replyPriority": 90}',
                        },
                    ),
                    _node("end", "END", {"outputVariable": "unused"}),
                ],
                edges=[
                    _edge("start", "low_reply"),
                    _edge("low_reply", "high_reply"),
                    _edge("high_reply", "end"),
                ],
            )
            started = _start_chatflow(client, chatflow["id"])
            terminal = _wait_for_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"]["answer"], "high priority reply")
        self.assertEqual(terminal["output"]["replyPriority"], 90)
        self.assertEqual(_assistant_messages(events), ["high priority reply"])

    def test_side_effect_only_chatflow_returns_no_reply_summary_without_assistant_message(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(
                client,
                nodes=[
                    _node("start", "START"),
                    _node(
                        "notify",
                        "CODE",
                        {
                            "sideEffectTerminal": True,
                            "code": (
                                "result = {"
                                '"sideEffectOnly": True, '
                                '"deliveryStatus": "sent", '
                                '"sideEffectEvidence": {"channel": "email", "idempotencyKey": "notify-2144"}'
                                "}"
                            ),
                        },
                    ),
                    _node("end", "END"),
                ],
                edges=[_edge("start", "notify")],
            )
            started = _start_chatflow(client, chatflow["id"])
            terminal = _wait_for_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertTrue(terminal["output"]["noReply"])
        self.assertTrue(terminal["output"]["sideEffectOnly"])
        self.assertEqual(terminal["output"]["summary"], "side_effect_only_completed")
        self.assertEqual(terminal["output"]["sideEffectEvidence"][0]["nodeKey"], "notify")
        self.assertEqual(_assistant_messages(events), [])


def _create_chatflow(
    client: TestClient,
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Chatflow Final Output Rules {time.time_ns()}",
            "description": "spec 214.4 final-output fixture",
            "nodes": nodes,
            "edges": edges,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _start_chatflow(client: TestClient, chatflow_id: int) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/chatflows/{chatflow_id}/runs",
        json={
            "input": {
                "sys.query": "spec 214.4",
                "sys.conversation_id": f"final-output-{time.time_ns()}",
                "sys.user_id": "user-final-output-2144",
                "sys.channel": "web",
            }
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _wait_for_result(client: TestClient, result_ref: str, timeout: float = 5.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] in {"SUCCEEDED", "FAILED", "INTERRUPTED", "CANCELLED"}:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for terminal result; latest={latest}")


def _assistant_messages(events: list[dict[str, Any]]) -> list[str]:
    return [
        str(event["payload"]["content"])
        for event in events
        if event.get("type") == "assistant_message"
    ]


def _node(node_key: str, node_type: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"nodeKey": node_key, "type": node_type, "name": node_key, "config": config or {}}


def _edge(source: str, target: str, condition: str | None = None) -> dict[str, Any]:
    return {"sourceNodeKey": source, "targetNodeKey": target, "condition": condition}
