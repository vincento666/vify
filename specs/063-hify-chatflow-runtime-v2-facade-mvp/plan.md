# Plan 063: Hify Chatflow Runtime V2 Facade MVP

## Implementation Shape

Reuse 062:

```text
shared runtime core
  -> Chatflow facade
  -> chatflow_session projection
  -> chatflow_checkpoint projection
```

The existing 058 `runs-v2` behavior can be kept as the route contract, but the
execution should move to shared runtime core abstractions where feasible.

Chatflow-specific session/checkpoint rows are projections. The shared runtime
event store remains the authoritative event source.

External routers, including the SOP multi-level router, remain owners of
multi-intent switching. Chatflow v2 preserves caller context and returns
execution refs/results.

## Compatibility

Old endpoints remain:

```text
POST /api/v1/chatflows/{id}/runs
```

Old `Accept: text/event-stream` remains replay. New v2 stream remains live.

Resume must be idempotent for the same checkpoint/input. Fallback or rejection
must be explicit and must not emit fake v2 live refs.

## Canvas Debug Projection

When Chatflow debug uses v2 mode, the canvas and debug panel consume runtime v2
refs/events:

```text
run refs -> node status/events -> canvas node state
                          -> debug panel node rows
```

Running animation, completed state, waiting state, skipped state, and failed
state are projections of runtime v2 node status. A node error stops the v2 debug
run and emits terminal failure evidence unless a supported error/fallback edge
exists.

## Unsupported Graphs

Early v2 coverage is graph-level:

```text
if unsupported nodes exist:
  return unsupported report or full-run fallback
else:
  run v2
```

Do not execute supported nodes in v2 and unsupported nodes in v1 inside the same
run.
