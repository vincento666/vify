from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from tests.integration.runtime.load._helpers import (
    assert_terminal_results,
    configure_load_database_pool,
    count_runtime_jobs_for_runs,
    create_linear_workflow,
    drain_workflow_jobs,
    latency_percentiles,
    reset_load_database_pool,
    runtime_job_ids_for_runs,
    start_concurrently,
)


@pytest.fixture(autouse=True)
def _runtime_mid_pressure_database_pool(monkeypatch: pytest.MonkeyPatch):
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


@pytest.mark.parametrize("concurrency", [100, 150, 200])
def test_local_100_200_concurrent_runs_stay_within_mid_pressure_thresholds(concurrency: int) -> None:
    with TestClient(app) as client:
        workflow = create_linear_workflow(
            client,
            name=f"Runtime V2 Mid Pressure {concurrency}",
            description="spec 221.2 local 100-200 mid-pressure smoke fixture",
        )
        started = start_concurrently(
            client,
            int(workflow["id"]),
            concurrency,
            timeout=240,
            input_prefix="pressure",
        )
        run_ids = {sample.run_id for sample in started}
        assert count_runtime_jobs_for_runs(run_ids, status="QUEUED") == concurrency
        job_ids = runtime_job_ids_for_runs(run_ids, status="QUEUED")
        assert len(job_ids) == concurrency
        drained = drain_workflow_jobs(job_ids, worker_count=16, timeout=240)
        samples = assert_terminal_results(client, started, input_prefix="pressure")
        assert drained >= concurrency

    percentiles = latency_percentiles(samples)
    print(
        "capacity_metrics "
        f"slice=221.2 concurrency={concurrency} "
        f"p50_ms={percentiles['p50']:.2f} "
        f"p95_ms={percentiles['p95']:.2f} "
        f"p99_ms={percentiles['p99']:.2f} "
        f"events={sum(sample.event_count for sample in samples)} "
        f"queue_states={','.join(sorted({sample.queue_state for sample in samples}))}",
        flush=True,
    )
    assert len(samples) == concurrency
    assert {sample.index for sample in samples} == set(range(concurrency))
    assert {sample.queue_state for sample in samples} <= {"queued", "running", "unknown"}
    assert sum(sample.event_count for sample in samples) >= concurrency * 3
    assert percentiles["p99"] < 120_000
