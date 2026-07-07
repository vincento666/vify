from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import Base, get_session_factory, reset_engine_cache
from app.modules.workflow.runtime_job_worker import build_workflow_runtime_job_worker


@dataclass(frozen=True)
class RunSample:
    index: int
    elapsed_ms: float
    event_count: int
    queue_state: str


@dataclass(frozen=True)
class StartSample:
    index: int
    run_id: int
    result_ref: str
    events_ref: str
    started_at: float
    elapsed_ms: float
    queue_state: str


def configure_load_database_pool(monkeypatch: Any, *, pool_size: int, max_overflow: int, timeout_seconds: int) -> None:
    monkeypatch.setenv("HIFY_DATABASE_POOL_SIZE", str(pool_size))
    monkeypatch.setenv("HIFY_DATABASE_MAX_OVERFLOW", str(max_overflow))
    monkeypatch.setenv("HIFY_DATABASE_POOL_TIMEOUT_SECONDS", str(timeout_seconds))
    get_settings.cache_clear()
    reset_engine_cache()


def reset_load_database_pool() -> None:
    get_settings.cache_clear()
    reset_engine_cache()


def run_concurrently(
    client: TestClient,
    workflow_id: int,
    concurrency: int,
    *,
    timeout: float,
    input_prefix: str,
) -> list[RunSample]:
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(_execute_one_run, client, workflow_id, index, input_prefix)
            for index in range(concurrency)
        ]
        return [future.result() for future in as_completed(futures, timeout=timeout)]


def start_concurrently(
    client: TestClient,
    workflow_id: int,
    concurrency: int,
    *,
    timeout: float,
    input_prefix: str,
) -> list[StartSample]:
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(_start_one_run, client, workflow_id, index, input_prefix)
            for index in range(concurrency)
        ]
        return [future.result() for future in as_completed(futures, timeout=timeout)]


def drain_workflow_jobs(job_ids: list[int], *, worker_count: int, timeout: float = 120.0) -> int:
    deadline = time.monotonic() + timeout
    pending = list(job_ids)

    def drain(worker_index: int) -> int:
        claimed = 0
        while time.monotonic() < deadline:
            if not pending:
                return claimed
            try:
                job_id = pending.pop()
            except IndexError:
                return claimed
            with get_session_factory()() as session:
                result = build_workflow_runtime_job_worker(
                    session,
                    worker_id=f"load-worker-{worker_index}",
                    lease_seconds=120,
                ).run_once(job_id=job_id)
            assert result["claimed"], result
            assert result["status"] == "COMPLETED", result
            claimed += 1
        raise AssertionError(f"Timed out draining runtime jobs; worker={worker_index} claimed={claimed}")

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        return sum(executor.map(drain, range(worker_count)))


def assert_terminal_results(client: TestClient, samples: list[StartSample], *, input_prefix: str) -> list[RunSample]:
    results: list[RunSample] = []
    for sample in samples:
        terminal = wait_for_result(client, sample.result_ref)
        events = client.get(sample.events_ref).json()["data"]["list"]
        assert terminal["status"] == "SUCCEEDED", terminal
        assert terminal["output"] == {"final": f"ok {input_prefix}-{sample.index}"}
        assert_event_sequence(events)
        results.append(
            RunSample(
                index=sample.index,
                elapsed_ms=(time.perf_counter() - sample.started_at) * 1000,
                event_count=len(events),
                queue_state=sample.queue_state,
            )
        )
    return results


def count_runtime_jobs_for_runs(run_ids: set[int], *, status: str | None = None) -> int:
    job_table = Base.metadata.tables["runtime_jobs"]
    with get_session_factory()() as session:
        query = sa.select(sa.func.count()).select_from(job_table).where(
            job_table.c.run_id.in_(run_ids),
            job_table.c.deleted.is_(False),
        )
        if status is not None:
            query = query.where(job_table.c.status == status)
        return int(session.execute(query).scalar_one())


def runtime_job_ids_for_runs(run_ids: set[int], *, status: str | None = None) -> list[int]:
    job_table = Base.metadata.tables["runtime_jobs"]
    with get_session_factory()() as session:
        query = sa.select(job_table.c.id).where(
            job_table.c.run_id.in_(run_ids),
            job_table.c.deleted.is_(False),
        )
        if status is not None:
            query = query.where(job_table.c.status == status)
        return [int(row[0]) for row in session.execute(query).all()]


def create_linear_workflow(client: TestClient, *, name: str, description: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"{name} {datetime.now().timestamp()}",
            "description": description,
            "nodes": [
                _node("start", "START"),
                _node("message", "MESSAGE", {"content": "ok {{start.sys.query}}", "outputVariable": "answer"}),
                _node("end", "END", {"outputVariable": "final", "output": "{{message.answer}}"}),
            ],
            "edges": [_edge("start", "message"), _edge("message", "end")],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def latency_percentiles(samples: list[RunSample]) -> dict[str, float]:
    values = sorted(sample.elapsed_ms for sample in samples)
    return {
        "p50": _percentile(values, 0.50),
        "p95": _percentile(values, 0.95),
        "p99": _percentile(values, 0.99),
    }


def _execute_one_run(client: TestClient, workflow_id: int, index: int, input_prefix: str) -> RunSample:
    query = f"{input_prefix}-{index}"
    started_at = time.perf_counter()
    started = client.post(
        f"/api/v1/workflows/{workflow_id}/runs",
        json={"input": {"sys.query": query}},
    )
    assert started.status_code == 200, started.text
    envelope = started.json()["data"]
    terminal = wait_for_result(client, envelope["resultRef"])
    events = client.get(envelope["eventsRef"]).json()["data"]["list"]
    elapsed_ms = (time.perf_counter() - started_at) * 1000

    assert terminal["status"] == "SUCCEEDED", terminal
    assert terminal["output"] == {"final": f"ok {query}"}
    assert_event_sequence(events)
    queue_state = str(envelope.get("queueState", {}).get("status", "unknown"))
    return RunSample(index=index, elapsed_ms=elapsed_ms, event_count=len(events), queue_state=queue_state)


def _start_one_run(client: TestClient, workflow_id: int, index: int, input_prefix: str) -> StartSample:
    started_at = time.perf_counter()
    started = client.post(
        f"/api/v1/workflows/{workflow_id}/runs",
        json={"input": {"sys.query": f"{input_prefix}-{index}"}},
    )
    assert started.status_code == 200, started.text
    envelope = started.json()["data"]
    assert envelope["status"] == "RUNNING", envelope
    queue_state = str(envelope.get("queueState", {}).get("status", "unknown"))
    assert queue_state != "rejected", envelope.get("queueState")
    return StartSample(
        index=index,
        run_id=int(envelope["runId"]),
        result_ref=str(envelope["resultRef"]),
        events_ref=str(envelope["eventsRef"]),
        started_at=started_at,
        elapsed_ms=(time.perf_counter() - started_at) * 1000,
        queue_state=queue_state,
    )


def wait_for_result(
    client: TestClient,
    result_ref: str,
    wanted_status: str | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        response = client.get(result_ref)
        assert response.status_code == 200, response.text
        latest = response.json()["data"]
        if latest["status"] in {"SUCCEEDED", "FAILED", "INTERRUPTED", "CANCELLED"}:
            if wanted_status is not None and latest["status"] != wanted_status:
                raise AssertionError(f"Expected {wanted_status}, got {latest}")
            return latest
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for terminal result; latest={latest}")


def assert_event_sequence(events: list[dict[str, Any]]) -> None:
    sequences = [int(event["sequence"]) for event in events]
    assert sequences == sorted(sequences)
    assert len(sequences) == len(set(sequences))
    assert sequences[0] == 1
    assert {"workflow_run_started", "workflow_node_completed", "workflow_run_completed"}.issubset(
        {event["type"] for event in events}
    )


def _percentile(sorted_values: list[float], quantile: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, round((len(sorted_values) - 1) * quantile))
    return sorted_values[index]


def _node(node_key: str, node_type: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"nodeKey": node_key, "type": node_type, "name": node_key, "config": config or {}}


def _edge(source: str, target: str) -> dict[str, Any]:
    return {"sourceNodeKey": source, "targetNodeKey": target, "condition": None}
