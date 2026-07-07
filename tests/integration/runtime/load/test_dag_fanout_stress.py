from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from tests.integration.runtime.load._helpers import (
    assert_event_sequence,
    configure_load_database_pool,
    count_runtime_jobs_for_runs,
    drain_workflow_jobs,
    reset_load_database_pool,
    runtime_job_ids_for_runs,
    start_concurrently,
    wait_for_result,
)


@pytest.fixture(autouse=True)
def _runtime_fanout_stress_pool(monkeypatch: pytest.MonkeyPatch):
    configure_load_database_pool(monkeypatch, pool_size=64, max_overflow=32, timeout_seconds=90)
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        runtime_v2_request_thread_completion_enabled=False,
    )
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_settings, None)
        reset_load_database_pool()


@pytest.mark.parametrize("branch_count", [10, 20])
def test_dag_fanout_stress_preserves_branch_results_and_events(branch_count: int) -> None:
    run_count = 50
    with TestClient(app) as client:
        workflow = _create_fanout_workflow(client, branch_count=branch_count)
        started = start_concurrently(
            client,
            int(workflow["id"]),
            run_count,
            timeout=180,
            input_prefix=f"fanout-{branch_count}",
        )
        run_ids = {sample.run_id for sample in started}
        assert count_runtime_jobs_for_runs(run_ids, status="QUEUED") == run_count
        job_ids = runtime_job_ids_for_runs(run_ids, status="QUEUED")
        assert len(job_ids) == run_count

        drained = drain_workflow_jobs(job_ids, worker_count=16, timeout=240)
        assert drained == run_count

        for sample in started:
            terminal = wait_for_result(client, sample.result_ref, timeout=30)
            events = client.get(sample.events_ref).json()["data"]["list"]
            assert terminal["status"] == "SUCCEEDED", terminal
            assert terminal["output"] == {
                "final": _expected_output(branch_count, f"fanout-{branch_count}-{sample.index}")
            }
            assert_event_sequence(events)
            completed_nodes = {
                str(event.get("nodeId"))
                for event in events
                if event.get("type") == "workflow_node_completed"
            }
            assert completed_nodes == {
                *{_branch_key(index) for index in range(branch_count)},
                "end",
            }


def _create_fanout_workflow(client: TestClient, *, branch_count: int) -> dict[str, Any]:
    nodes = [
        {
            "nodeKey": "start",
            "type": "START",
            "name": "Start",
            "config": {"ports": [{"key": "default", "allowFanOut": True}]},
        },
        *[
            {
                "nodeKey": _branch_key(index),
                "type": "MESSAGE",
                "name": f"Branch {index}",
                "config": {
                    "content": f"branch-{index:02d} {{{{start.sys.query}}}}",
                    "outputVariable": "answer",
                },
            }
            for index in range(branch_count)
        ],
        {
            "nodeKey": "end",
            "type": "END",
            "name": "End",
            "config": {
                "outputVariable": "final",
                "output": "|".join(f"{{{{{_branch_key(index)}.answer}}}}" for index in range(branch_count)),
            },
        },
    ]
    edges = [
        *[
            {"sourceNodeKey": "start", "targetNodeKey": _branch_key(index), "condition": None}
            for index in range(branch_count)
        ],
        *[
            {"sourceNodeKey": _branch_key(index), "targetNodeKey": "end", "condition": None}
            for index in range(branch_count)
        ],
    ]
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime V2 Fanout Stress {branch_count} {datetime.now().timestamp()}",
            "description": "spec 221.4 DAG fan-out stress fixture",
            "nodes": nodes,
            "edges": edges,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _branch_key(index: int) -> str:
    return f"branch_{index:02d}"


def _expected_output(branch_count: int, query: str) -> str:
    return "|".join(f"branch-{index:02d} {query}" for index in range(branch_count))
