# Spec 125: Runtime V2 Version Targeting UI

## Status

Slice 125.1 implemented. Focused frontend, rem, and browser UAT are green; full
frontend unit/build were attempted and are blocked by out-of-scope
customer-assistant failures already present in the shared worktree.

## User Story

As a workflow or chatflow operator, I can test any published version from the
publish dialog through runtime v2, so I can prove async execution pinned the
selected immutable snapshot without changing the active published version.

## Functional Requirements

- Frontend runtime v2 API helpers accept optional `versionId` for Workflow and
  Chatflow starts.
- The publish dialog version list keeps the existing published-run test action.
- The same version list adds a product-visible runtime v2 test action for each
  published version.
- Runtime v2 test results display `runId`, `version`, `versionId`, `status`, and
  a debug or result reference when the backend returns one.
- The UI must make the runtime-v2 path distinguishable from the existing
  published-run test path.

## Non-Goals

- Backend runtime v2 targeting changes; slice 120 owns that behavior.
- Reworking publish, rollback, or version-list layout outside the focused
  action/result additions.
- Customer-assistant file changes.

## Acceptance Criteria

- RED frontend evidence proves `runWorkflowV2`/`runChatflowV2` do not send
  explicit `versionId` before implementation.
- Frontend API coverage verifies optional `versionId` payloads for both helpers.
- UI contract coverage verifies the version list exposes both published-run and
  runtime-v2 test actions plus the runtime-v2 result fields.
- Browser UAT creates/publishes v1 and v2, opens the publish dialog, runs a
  runtime-v2 test for a selected historical version, and confirms visible
  `versionId`, status, and debug/result reference.
- Focused frontend tests, rem gate, full frontend unit, and build gates are
  green.

## Evidence

- RED: `artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/red.txt`
- Focused frontend: `artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/frontend-focused.txt`
- Frontend rem: `artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/frontend-rem.txt`
- Frontend unit: `artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/frontend-unit.txt`
- Frontend build: `artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/frontend-build.txt`
- Browser UAT: `artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/uat.md`
- Browser UAT log: `artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/browser-uat.txt`
- Browser UAT screenshot:
  `artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/screenshots/runtime-v2-version-targeting-ui.png`
