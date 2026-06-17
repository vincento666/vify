# Plan 120: Runtime V2 Published Version Targeting

## Slice 120.1 Published Snapshot Selection

1. Add backend integration tests for explicit runtime v2 `versionId` targeting.
2. Capture RED output before changing runtime implementation.
3. Thread `WorkflowRunRequest.version_id` through both runtime v2 routes.
4. Select published snapshots through `WorkflowPublishRepository` for active and
   targeted runtime v2 starts.
5. Persist chosen version metadata and definition in `_runtimeV2` run input.
6. Verify result, debug, and resume paths read the persisted metadata/definition.
7. Run focused integration and ruff gates.
8. Update tasks/evidence and commit the focused slice.

## Design Notes

Runtime v2 already stores a full graph definition under `_runtimeV2.definition`
inside `workflow_run.input`. Completion, result, and resume should continue to
trust that stored definition rather than loading the mutable draft graph.

The new behavior should reuse the existing published-version lookup contract:
`None` selects the active row, an explicit id must match the same owner id and
flow type, and missing/cross-flow ids return `404`.

Chatflow runtime v2 currently reads draft graphs when no published snapshot is
selected. For this slice, once a Chatflow has an active published version,
runtime v2 should prefer the active published snapshot so active-vs-targeted
behavior matches Workflow v2 and runtime v1 published-run targeting.

## Evidence Directory

`artifacts/slices/120-runtime-v2-published-version-targeting/120.1/`
