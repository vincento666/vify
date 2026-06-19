# Plan 195: Runtime V2 Redis Stream Event Channel

## Architecture

1. Add a small runtime event stream bus abstraction under workflow infra.
2. Provide an in-memory implementation for deterministic tests and a Redis
   Streams implementation for configured production/dev environments.
3. Keep `ChatflowStateRepository` as the DB source of truth. After a successful
   event commit, publish the committed event row to the optional stream bus.
4. Thread the optional bus through runtime v2 route dependencies and background
   completion threads.
5. Teach the SSE iterator to read events from the bus first and fall back to
   `service.list_events()` when the stream has no newer events.

## Test Strategy

- Integration RED/GREEN:
  - `tests/integration/workflow/test_runtime_v2_redis_streams.py`
- Focused regression gates:
  - `tests/integration/workflow/test_runtime_v2_redis_streams.py`
  - `tests/integration/workflow/test_chatflow_runtime_v2_spike.py`
  - `tests/unit/workflow/test_runtime_v2_core.py`

## Evidence

Save command outputs in:

```text
artifacts/slices/195-runtime-v2-redis-stream-event-channel/195.1/
├── red.txt
├── integration.txt
├── regression.txt
├── slice-report.md
└── uat.md
```

## Risk Controls

- Swallow stream publish failures after DB commit so Redis outages do not lose
  durable facts.
- Do not modify frontend UI in this slice; rem gate is not required unless a
  later fix touches frontend visual files.
- Do not change old Chatflow SSE replay behavior.
