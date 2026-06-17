# 146 Customer Assistant Worker Skill Policy Profile

## Status

Complete.

## Goal

Extend configurable customer-assistant worker profiles from worker/model/prompt
metadata to skill policy metadata. A demo operator must be able to configure
and inspect the tool policy and structured output schema refs that the ReAct
worker uses, with MySQL persistence and visible worker evidence.

## Acceptance Criteria

- Worker profiles include `toolPolicyRef` and `outputSchemaRef` in default/env
  JSON, persisted overrides, API responses, and frontend update payloads.
- ReAct worker registry derives `toolPolicyRef` and `outputSchemaRef` from the
  active profile.
- React worker result evidence records the configured refs alongside model,
  prompt, tool refs, and risk policy.
- The operator workbench profile panel and edit form show/edit both refs.
- MySQL8 table metadata and compatibility migration cover the new columns.
- Focused backend/frontend tests, MySQL schema gate, rem/full frontend unit,
  build, and browser UAT pass.

## Non-Goals

- A separate skill-policy admin resource.
- Runtime validation of external policy definitions.
- Real external tool calling changes.

## Evidence

Evidence lives under
`artifacts/slices/146-customer-assistant-worker-skill-policy-profile/146.1/`.

- RED unit: `red-unit.txt`
- RED integration: `red-integration.txt`
- RED MySQL surface: `red-mysql-surface.txt`
- RED frontend: `red-frontend-panel.txt`
- Backend unit/focused: `unit-green.txt`
- MySQL metadata: `mysql-metadata-green.txt`
- MySQL-backed worker-profile integration: `integration-green.txt`,
  `worker-profiles-integration.txt`
- Ruff: `ruff.txt`
- Frontend focused/rem/unit/build: `frontend-focused-green.txt`,
  `view-model-green.txt`, `rem-green.txt`, `frontend-unit-final.txt`,
  `frontend-build.txt`
- Browser UAT: `browser-uat.txt`,
  `screenshots/customer-assistant-worker-profile-edit.png`
- Scans: `diff-secret-sqlite-scan.txt`, `rem-scan.txt`
