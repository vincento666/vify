# Spec 120: Runtime V2 Published Version Targeting

## Status

Slice 120.1 complete.

## User Story

As a workflow or chatflow maintainer, I can start runtime v2 against a specific
published version without changing the active published version, so async
execution, result inspection, debug detail, and resume all remain pinned to the
same immutable snapshot.

## Functional Requirements

- `POST /api/v1/workflows/{id}/runs-v2` accepts optional `versionId`.
- `POST /api/v1/chatflows/{id}/runs-v2` accepts optional `versionId`.
- Omitting `versionId` uses the current active published version when one
  exists.
- Providing `versionId` uses that published snapshot for the same owner and flow
  type.
- Runtime v2 start, stored run metadata, result, and debug detail expose the
  chosen `versionId` and `version`.
- Runtime v2 resume continues from the stored published snapshot even if the
  draft graph is edited after interruption.
- Unknown or cross-flow `versionId` returns `404` and does not create live
  runtime refs.

## Non-Goals

- Frontend controls for selecting a runtime v2 version.
- Browser UAT; this slice is backend-only.
- Changing publish, rollback, or active-version mutation semantics.
- Reworking runtime v1 published-run targeting.

## Acceptance Criteria

- RED evidence proves runtime v2 ignores or mishandles explicit `versionId`
  before implementation.
- Integration coverage verifies active-vs-targeted Workflow runtime v2.
- Integration coverage verifies active-vs-targeted Chatflow runtime v2.
- Integration coverage verifies unknown and cross-flow `versionId` rejection.
- Integration coverage verifies resume after draft edit still uses the targeted
  published version.
- Focused integration and ruff gates are green.

## Evidence

- RED: `artifacts/slices/120-runtime-v2-published-version-targeting/120.1/red.txt`
- Integration: `artifacts/slices/120-runtime-v2-published-version-targeting/120.1/integration.txt`
- Ruff: `artifacts/slices/120-runtime-v2-published-version-targeting/120.1/ruff.txt`
