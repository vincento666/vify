# Plan 125: Runtime V2 Version Targeting UI

## Slice 125.1 Published Version Runtime V2 Test

1. Add frontend API RED coverage for `versionId` payloads on runtime v2 starts.
2. Add UI contract RED coverage for the publish dialog runtime-v2 version action
   and result fields.
3. Thread optional `versionId` through `runWorkflowV2` and `runChatflowV2`.
4. Add a runtime-v2 test action beside the existing published-run action.
5. Show a separate runtime-v2 result block with `runId`, `version`, `versionId`,
   status, and debug/result reference.
6. Verify focused frontend, rem, full unit, and build gates.
7. Run browser UAT for v1/v2 publish dialog version targeting.
8. Update tasks/evidence and commit only slice 125 files.

## Design Notes

The existing publish dialog already exposes per-version published-run testing.
This slice adds a parallel runtime-v2 action rather than changing that action, so
operators can compare legacy published-run behavior with async runtime-v2
version targeting.

Runtime v2 starts already return async run references. The UI result block should
surface the backend response directly enough to prove the immutable version was
pinned, without opening the full debug dock.

## Evidence Directory

`artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/`
