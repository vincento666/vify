from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.integration.runtime.load._helpers import (
    assert_event_sequence,
    configure_load_database_pool,
    reset_load_database_pool,
    wait_for_result,
)


@dataclass(frozen=True)
class InterruptedRun:
    index: int
    run_id: int
    result_ref: str
    nodes_ref: str
    events_ref: str


@pytest.fixture(autouse=True)
def _runtime_resume_stress_pool(monkeypatch: pytest.MonkeyPatch):
    configure_load_database_pool(monkeypatch, pool_size=64, max_overflow=64, timeout_seconds=90)
    try:
        yield
    finally:
        reset_load_database_pool()


def test_resume_no_side_effect_replay_under_concurrent_interrupt_resume_stress() -> None:
    run_count = 50
    stamp = time.time_ns()
    with TestClient(app) as client:
        chatflow = _create_side_effect_then_question_chatflow(client, stamp)
        interrupted = _start_interrupted_runs(client, int(chatflow["id"]), run_count, stamp)

        for sample in interrupted:
            before_nodes = client.get(sample.nodes_ref).json()["data"]["list"]
            assert _node_run_count(before_nodes, "notify_1") == 1

        resumed = _resume_runs(client, interrupted, stamp)

        assert len(resumed) == run_count
        for payload in resumed:
            index = int(payload["index"])
            run = interrupted[index]
            after_nodes = client.get(run.nodes_ref).json()["data"]["list"]
            events = client.get(run.events_ref).json()["data"]["list"]
            notify_node = next(node for node in after_nodes if node["nodeKey"] == "notify_1")
            assert _node_run_count(after_nodes, "notify_1") == 1
            assert notify_node["outputs"]["sideEffect"] == f"sent-{stamp}"
            assert payload["status"] == "SUCCEEDED"
            assert payload["waitingNodeKeys"] == []
            assert payload["waitingNodes"] == []
            assert payload["output"] == {"final": f"answer=yes-{index} effect=sent-{stamp}"}
            assert_event_sequence(events)


def _start_interrupted_runs(
    client: TestClient,
    chatflow_id: int,
    run_count: int,
    stamp: int,
) -> list[InterruptedRun]:
    with ThreadPoolExecutor(max_workers=run_count) as executor:
        futures = [
            executor.submit(_start_one_interrupted_run, client, chatflow_id, index, stamp)
            for index in range(run_count)
        ]
        return [future.result() for future in as_completed(futures, timeout=180)]


def _start_one_interrupted_run(client: TestClient, chatflow_id: int, index: int, stamp: int) -> InterruptedRun:
    response = client.post(
        f"/api/v1/chatflows/{chatflow_id}/runs",
        json={
            "input": {
                "sys.query": f"resume-stress-{index}",
                "sys.conversation_id": f"resume-no-replay-{stamp}-{index}",
            }
        },
    )
    assert response.status_code == 200, response.text
    started = response.json()["data"]
    interrupted = wait_for_result(client, started["resultRef"], "INTERRUPTED", timeout=30)
    assert interrupted["waitingNodeKeys"] == ["question_1"]
    return InterruptedRun(
        index=index,
        run_id=int(started["runId"]),
        result_ref=str(started["resultRef"]),
        nodes_ref=str(started["nodesRef"]),
        events_ref=str(started["eventsRef"]),
    )


def _resume_runs(client: TestClient, runs: list[InterruptedRun], stamp: int) -> list[dict[str, Any]]:
    with ThreadPoolExecutor(max_workers=len(runs)) as executor:
        futures = [executor.submit(_resume_one_run, client, sample, stamp) for sample in runs]
        return [future.result() for future in as_completed(futures, timeout=180)]


def _resume_one_run(client: TestClient, sample: InterruptedRun, stamp: int) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/runtime-runs/{sample.run_id}/resume",
        json={
            "resumeData": {"answer": f"yes-{sample.index}"},
            "idempotencyKey": f"resume-no-replay-{stamp}-{sample.index}",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    payload["index"] = sample.index
    return payload


def _node_run_count(nodes: list[dict[str, Any]], node_key: str) -> int:
    return sum(1 for node in nodes if node["nodeKey"] == node_key)


def _create_side_effect_then_question_chatflow(client: TestClient, stamp: int) -> dict[str, Any]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"221.5 Resume No Replay Side Effect {stamp} {datetime.now().timestamp()}",
            "description": "spec 221.5 concurrent interrupt/resume no side-effect replay fixture",
            "nodes": [
                {
                    "nodeKey": "start",
                    "type": "START",
                    "name": "Start",
                    "config": {"ports": [{"key": "default", "allowFanOut": True}]},
                },
                {
                    "nodeKey": "notify_1",
                    "type": "CODE",
                    "name": "Notify",
                    "config": {
                        "language": "python",
                        "code": f"result = {{'sideEffect': 'sent-{stamp}'}}",
                        "outputParameters": [{"name": "sideEffect", "type": "string"}],
                    },
                },
                {
                    "nodeKey": "question_1",
                    "type": "QUESTION",
                    "name": "Confirm",
                    "config": {
                        "question": "确认继续？",
                        "answerType": "text",
                        "outputVariable": "answer",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {
                        "outputVariable": "final",
                        "output": "answer={{question_1.answer}} effect={{notify_1.sideEffect}}",
                    },
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "notify_1", "condition": None},
                {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
                {"sourceNodeKey": "notify_1", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "question_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]
