# Feature Spec: Runtime V2 SOP Debug Metadata Continuity

## Status

Complete.

## User Story

As an operator debugging Chatflow/Workflow runtime v2 from SOP and demo flows, I
can inspect any durable runtime event and still see the minimal caller and
version metadata needed to explain where the run came from and which definition
was executed.

## Functional Requirements

- Every runtime v2 L1 event must include redacted `callerContext` from the
  original run input when available.
- Events produced after start, including node started/completed/status,
  waiting/interrupted, resume, complete, fail, and cancel events, must retain the
  same `callerContext`.
- Events for published-version runs must include the same minimal
  `definitionSource`, `versionId`, and `version` metadata as the start/result
  payload.
- Do not copy the full `_runtimeV2.definition`, raw input, or node graph into
  every event.
- Do not add tables or migrations.

## Non-Goals

- No frontend changes.
- No event schema version bump.
- No change to runtime execution semantics.
- No new live provider calls.

## Acceptance Criteria

- RED shared-core integration fails before implementation because node and
  completion events have empty `callerContext`.
- RED published-version integration fails before implementation because node or
  completed/resume events lack `versionId/version/definitionSource`.
- After implementation, focused runtime v2 integration tests pass.
- Focused ruff passes for touched files.

## Evidence

Evidence lives under
`artifacts/slices/152-runtime-v2-sop-debug-metadata-continuity/152.1/`.

- RED shared core: `red-shared-core.txt`
- RED version targeting: `red-version-targeting.txt`
- Shared core integration: `shared-core.txt`
- Version targeting integration: `version-targeting.txt`
- Ruff: `ruff.txt`
