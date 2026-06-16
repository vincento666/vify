# Feature Spec: Workflow Published Run Version Targeting

## Status

Slice 098.1 complete.

## User Story

As a demo operator or workflow maintainer, I can run a specific published
Workflow/Chatflow version without changing the active published version, so
published demo behavior is explainable even when drafts and rollback state
change.

## Functional Requirements

- `POST /api/v1/workflows/{id}/published-runs` accepts optional `versionId`.
- `POST /api/v1/chatflows/{id}/published-runs` accepts optional `versionId`.
- Omitting `versionId` keeps the current active-version behavior.
- Providing `versionId` runs that immutable snapshot and returns the actual
  `versionId` and `version` used.
- Unknown or cross-flow `versionId` returns `404`.
- Running a historical version must not change the active published version.
- Frontend API helpers can pass an optional target version.
- Existing publish dialog version list exposes a lightweight test-run action for
  each version.

## Non-Goals

- Rebuilding the publish dialog layout.
- Changing draft publish validation rules.
- Replacing active/rollback semantics.

## Acceptance Criteria

- RED backend evidence proves explicit `versionId` is ignored/missing before
  implementation.
- Backend integration verifies active default, targeted historical run, unknown
  version error, and Chatflow parity.
- Frontend API/unit coverage verifies `versionId` request payloads.
- Browser UAT runs v1 and v2 snapshots explicitly and confirms active behavior
  remains stable.

## Evidence

- RED backend: `artifacts/slices/098-workflow-published-run-version-targeting/098.1/red-backend.txt`
- RED frontend: `artifacts/slices/098-workflow-published-run-version-targeting/098.1/red-frontend.txt`
- Backend workflow integration: `artifacts/slices/098-workflow-published-run-version-targeting/098.1/backend-workflow.txt`
- Backend focused publish versions: `artifacts/slices/098-workflow-published-run-version-targeting/098.1/backend-publish-versions.txt`
- Ruff: `artifacts/slices/098-workflow-published-run-version-targeting/098.1/ruff.txt`
- Frontend focused: `artifacts/slices/098-workflow-published-run-version-targeting/098.1/frontend-focused.txt`
- Frontend rem gate: `artifacts/slices/098-workflow-published-run-version-targeting/098.1/frontend-rem.txt`
- Frontend build: `artifacts/slices/098-workflow-published-run-version-targeting/098.1/frontend-build.txt`
- Browser UAT: `artifacts/slices/098-workflow-published-run-version-targeting/098.1/uat.txt`
- Browser UAT screenshot: `artifacts/slices/098-workflow-published-run-version-targeting/098.1/workflow-version-targeting.png`
