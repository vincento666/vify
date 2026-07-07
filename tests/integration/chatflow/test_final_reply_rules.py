import time
import unittest
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


class ChatflowFinalReplyRulesDagTest(unittest.TestCase):
    def test_end_output_wins_over_parallel_priority_candidates(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(
                client,
                nodes=[
                    _fanout_start(),
                    _code("reply_a", {"answer": "candidate a", "replyPriority": 100}),
                    _code("reply_b", {"answer": "candidate b", "replyPriority": 10}),
                    _node("end", "END", {"outputVariable": "final", "output": "end wins"}),
                ],
                edges=[
                    _edge("start", "reply_a"),
                    _edge("start", "reply_b"),
                    _edge("reply_a", "end"),
                    _edge("reply_b", "end"),
                ],
            )
            terminal, events = _run_chatflow(client, int(chatflow["id"]))

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "end wins"})
        self.assertEqual(_assistant_messages(events), ["end wins"])

    def test_answer_mapping_ignores_side_effect_only_branch_candidates(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(
                client,
                nodes=[
                    _fanout_start(),
                    _code("visible_reply", {"answer": "visible reply"}),
                    _code(
                        "notify",
                        {
                            "sideEffectOnly": True,
                            "answer": "internal notification text",
                            "sideEffectEvidence": {"channel": "email", "idempotencyKey": "notify-2162"},
                        },
                    ),
                    _node("end", "END", {"outputVariable": "unused"}),
                ],
                edges=[
                    _edge("start", "visible_reply"),
                    _edge("start", "notify"),
                    _edge("visible_reply", "end"),
                    _edge("notify", "end"),
                ],
            )
            terminal, events = _run_chatflow(client, int(chatflow["id"]))

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"answer": "visible reply"})
        self.assertEqual(_assistant_messages(events), ["visible reply"])

    def test_highest_priority_reply_wins_across_parallel_paths(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(
                client,
                nodes=[
                    _fanout_start(),
                    _code("low_reply", {"answer": "low priority", "replyPriority": 5}),
                    _code("high_reply", {"answer": "high priority", "replyPriority": 80}),
                    _node("end", "END", {"outputVariable": "unused"}),
                ],
                edges=[
                    _edge("start", "low_reply"),
                    _edge("start", "high_reply"),
                    _edge("low_reply", "end"),
                    _edge("high_reply", "end"),
                ],
            )
            terminal, events = _run_chatflow(client, int(chatflow["id"]))

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"]["answer"], "high priority")
        self.assertEqual(terminal["output"]["replyPriority"], 80)
        self.assertEqual(_assistant_messages(events), ["high priority"])

    def test_all_side_effect_only_paths_return_structured_no_reply_summary(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(
                client,
                nodes=[
                    _fanout_start(),
                    _code(
                        "notify_email",
                        {
                            "sideEffectOnly": True,
                            "deliveryStatus": "sent",
                            "sideEffectEvidence": {"channel": "email", "idempotencyKey": "email-2162"},
                        },
                        {"sideEffectTerminal": True},
                    ),
                    _code(
                        "notify_sms",
                        {
                            "sideEffectOnly": True,
                            "deliveryStatus": "sent",
                            "sideEffectEvidence": {"channel": "sms", "idempotencyKey": "sms-2162"},
                        },
                        {"sideEffectTerminal": True},
                    ),
                ],
                edges=[
                    _edge("start", "notify_email"),
                    _edge("start", "notify_sms"),
                ],
            )
            terminal, events = _run_chatflow(client, int(chatflow["id"]))

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertTrue(terminal["output"]["noReply"])
        self.assertTrue(terminal["output"]["sideEffectOnly"])
        self.assertEqual(terminal["output"]["summary"], "side_effect_only_completed")
        self.assertEqual(
            [item["nodeKey"] for item in terminal["output"]["sideEffectEvidence"]],
            ["notify_email", "notify_sms"],
        )
        self.assertEqual(_assistant_messages(events), [])


def _run_chatflow(client: TestClient, chatflow_id: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    started = _start_chatflow(client, chatflow_id)
    terminal = _wait_for_result(client, started["resultRef"])
    events = client.get(started["eventsRef"]).json()["data"]["list"]
    return terminal, events


def _create_chatflow(
    client: TestClient,
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Chatflow Final Reply Rules DAG {time.time_ns()}",
            "description": "spec 216.2 final reply fixture",
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
                "sys.query": "spec 216.2",
                "sys.conversation_id": f"final-reply-{time.time_ns()}",
                "sys.user_id": "user-final-reply-2162",
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


def _fanout_start() -> dict[str, Any]:
    return _node("start", "START", {"ports": [{"key": "default", "allowFanOut": True}]})


def _code(
    node_key: str,
    output: dict[str, Any],
    extra_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _node(
        node_key,
        "CODE",
        {
            "language": "python",
            "code": f"result = {output!r}",
            **(extra_config or {}),
        },
    )


def _node(node_key: str, node_type: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"nodeKey": node_key, "type": node_type, "name": node_key, "config": config or {}}


def _edge(source: str, target: str, condition: str | None = None) -> dict[str, Any]:
    return {"sourceNodeKey": source, "targetNodeKey": target, "condition": condition}
