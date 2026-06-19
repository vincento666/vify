#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time

from app.core.config import get_settings
from app.core.database import get_session_factory, initialise_database
from app.modules.workflow.infra.realtime.redis_streams import RedisRuntimeEventStreamBus, RuntimeEventStreamBus
from app.modules.workflow.runtime_job_worker import build_workflow_runtime_job_worker, default_runtime_job_worker_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Workflow Runtime Core jobs.")
    parser.add_argument("--once", action="store_true", help="Claim and run at most one job.")
    parser.add_argument("--worker-id", default=None, help="Stable worker id used for job leases.")
    parser.add_argument("--lease-seconds", type=int, default=300)
    parser.add_argument("--poll-interval", type=float, default=1.0)
    args = parser.parse_args()

    initialise_database()
    worker_id = args.worker_id or default_runtime_job_worker_id()
    session_factory = get_session_factory()
    event_stream_bus = _runtime_event_stream_bus()

    while True:
        with session_factory() as session:
            worker = build_workflow_runtime_job_worker(
                session,
                worker_id=worker_id,
                lease_seconds=args.lease_seconds,
                event_stream_bus=event_stream_bus,
            )
            result = worker.run_once()
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if args.once:
            return
        if not result.get("claimed"):
            time.sleep(max(0.1, args.poll_interval))


def _runtime_event_stream_bus() -> RuntimeEventStreamBus | None:
    redis_url = get_settings().redis_url
    if not redis_url:
        return None
    return RedisRuntimeEventStreamBus.from_url(redis_url)


if __name__ == "__main__":
    main()
