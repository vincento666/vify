# Feature Spec: Customer Assistant Test DB Isolation

## Status

Complete.

## User Story

As a maintainer of the MVP demo gates, I can run customer-assistant integration
tests together without a previous demo seed test leaving `HIFY_DATABASE_URL`
pointing at a deleted temporary SQLite file.

## Functional Requirements

- Demo seed tests that temporarily set `HIFY_DATABASE_URL` must restore the
  previous value before their temporary directory is removed.
- Settings cache must be cleared whenever the database URL is switched or
  restored.
- The focused customer-assistant integration combination must pass in one
  command.

## Non-Goals

- Reworking the global database helper.
- Changing application runtime database behavior.
- MySQL demo gate implementation; this slice only stabilizes local test
  isolation.

## Acceptance Criteria

- RED combined integration command fails with `sqlite3.OperationalError:
  unable to open database file`.
- After the fix, the same combined command passes.
- Ruff passes for the touched test files.

## Evidence

Evidence lives under
`artifacts/slices/128-customer-assistant-test-db-isolation/128.1/`.

- RED: `red.txt`
- Focused integration: `integration-focused.txt`
- Full customer-assistant integration: `integration-customer-assistant.txt`
- Ruff: `ruff.txt`
