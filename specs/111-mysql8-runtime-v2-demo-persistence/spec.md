# Spec 111: MySQL8 Runtime V2 Demo Persistence Evidence

## Status

Slice 111.1 complete. Local deterministic MySQL8 schema/dialect and JSON/text
round-trip evidence is green; opt-in real MySQL execution was skipped because
`HIFY_MYSQL8_TEST_DATABASE_URL` was not set.

## Goal

Prove the current productized MVP demo persistence boundary is compatible with
MySQL8 before runtime v2 events, checkpoints, chatflow configuration, workflow
published versions, and customer-assistant state become a hard demo
prerequisite.

## Acceptance Criteria

- A deterministic local MySQL8 schema/dialect gate covers the same MVP demo
  table set used by the real MySQL8 persistence smoke.
- The covered table set includes runtime v2 Chatflow sessions/events/
  checkpoints, Chatflow channel config, Workflow published versions, RuntimeLab
  sessions/tasks/checkpoints/events/commands, and customer assistant sessions,
  runs, tasks, events, worker runs/events, proposed actions, and worker profile
  overrides.
- Demo seed anchor fields and representative worker profile override JSON/text
  payloads round-trip safely through the persistence layer used by the test
  suite.
- The existing opt-in real MySQL8 command remains available through
  `HIFY_MYSQL8_TEST_DATABASE_URL`; when it is not set, evidence must clearly
  state that real MySQL was skipped.

## Non-goals

- Do not provision MySQL automatically.
- Do not introduce Alembic migrations.
- Do not modify customer-assistant feature behavior, Runtime Lab adapters, seed
  behavior, or UI flows except for a true schema compatibility fix.

## Evidence

Evidence lives under
`artifacts/slices/111-mysql8-runtime-v2-demo-persistence/111.1/`.

- RED:
  `artifacts/slices/111-mysql8-runtime-v2-demo-persistence/111.1/red.txt`
- MySQL8 lane:
  `artifacts/slices/111-mysql8-runtime-v2-demo-persistence/111.1/integration.txt`
- Ruff:
  `artifacts/slices/111-mysql8-runtime-v2-demo-persistence/111.1/ruff.txt`
- Browser UAT:
  `artifacts/slices/111-mysql8-runtime-v2-demo-persistence/111.1/uat.md`
