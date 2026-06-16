# Plan 065: Hify Workflow Runtime V2 Facade MVP

## API Shape

Candidate routes:

```text
POST /api/v1/workflows/{workflowId}/runs-v2
GET  /api/v1/runtime-runs/{runId}
GET  /api/v1/runtime-runs/{runId}/events
GET  /api/v1/runtime-runs/{runId}/events/stream
GET  /api/v1/runtime-runs/{runId}/result
```

Reuse the shared runtime routes from 062 where possible.

## Workflow-Specific Behavior

Workflow does not need:

- chatflow session id;
- channel/user conversation state;
- question/human checkpoint projection unless the node itself requires it.

It does need:

- input/output fidelity;
- observe/debug compatibility;
- node run details.
- workflow version/snapshot metadata;
- idempotent create behavior when a request key is supplied.

Workflow v2 runs must use a stable published/snapshot definition. Draft edits
must not change an in-flight run.

## Canvas Debug Projection

When Workflow debug uses v2 mode, the canvas and debug panel consume runtime v2
refs/events:

```text
run refs -> node status/events -> canvas node state
                          -> debug panel node rows
```

Running animation, completed state, waiting state, skipped state, and failed
state are projections of runtime v2 node status. A node error stops the v2 debug
run and emits terminal failure evidence unless a supported error/fallback edge
exists.

## Compatibility

The old sync Workflow endpoint remains the default.
