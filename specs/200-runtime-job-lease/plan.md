# Plan

## Slice 200.1 Runtime Job Lease MVP

1. Add RED repository tests for runtime job enqueue, claim, heartbeat, active
   lease exclusion, expired lease takeover, completion, and failure.
2. Add RED API integration coverage that a Workflow Run Gateway start produces
   a durable runtime job and the current inline worker marks it completed.
3. Register `runtime_jobs` in `app/core/schema.py` and startup compatibility
   migration checks.
4. Implement `RuntimeJobRepository` under workflow infra.
5. Wire Workflow Run Gateway completion through `RuntimeJobRepository` while
   keeping the existing in-process background thread for this slice.
6. Keep worker lease internals out of the public run response.
7. Run backend focused gates, broad workflow/runtime regression, frontend
   rem/unit, and browser UAT.

## Risks

- This slice proves durable job metadata and lease fencing, not a real external
  worker process.
- SQLite/MySQL concurrency semantics differ; repository tests cover local lease
  behavior, while multi-process row locking is deferred.
- Chatflow turn-level durability remains a later slice.
