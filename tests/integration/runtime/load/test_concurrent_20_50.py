from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.integration.runtime.load._helpers import (
    configure_load_database_pool,
    create_linear_workflow,
    latency_percentiles,
    reset_load_database_pool,
    run_concurrently,
)


@pytest.fixture(autouse=True)
def _runtime_load_database_pool(monkeypatch: pytest.MonkeyPatch):
    configure_load_database_pool(monkeypatch, pool_size=64, max_overflow=64, timeout_seconds=60)
    try:
        yield
    finally:
        reset_load_database_pool()


@pytest.mark.parametrize("concurrency", [20, 35, 50])
def test_local_20_50_concurrent_runs_complete_with_monotonic_events(concurrency: int) -> None:
    with TestClient(app) as client:
        workflow = create_linear_workflow(
            client,
            name=f"Runtime V2 Local {concurrency}",
            description="spec 221.1 local concurrency acceptance fixture",
        )

        samples = run_concurrently(
            client,
            int(workflow["id"]),
            concurrency,
            timeout=120,
            input_prefix="load",
        )

    percentiles = latency_percentiles(samples)
    print(
        "capacity_metrics "
        f"slice=221.1 concurrency={concurrency} "
        f"p50_ms={percentiles['p50']:.2f} "
        f"p95_ms={percentiles['p95']:.2f} "
        f"p99_ms={percentiles['p99']:.2f} "
        f"events={sum(sample.event_count for sample in samples)}",
        flush=True,
    )
    assert len(samples) == concurrency
    assert {sample.index for sample in samples} == set(range(concurrency))
    assert sum(sample.event_count for sample in samples) >= concurrency * 3
