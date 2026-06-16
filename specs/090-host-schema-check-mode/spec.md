# Spec 090: Host Schema Check Mode

## Goal

Give host-managed deployments an explicit startup mode that validates database
schema readiness without running hidden `create_all` or compatibility DDL.

## Acceptance Criteria

- `HIFY_PERSISTENCE_MODE=check` runs a schema check at startup and does not call
  `initialise_database()`.
- The schema check reports missing tables and missing columns with concrete
  names.
- The schema check uses the current dialect-aware table set, so MySQL demo mode
  does not require pgvector-only relational vector tables.
- Local/test startup behavior remains unchanged.

## Non-goals

- Do not add Alembic migrations in this slice.
- Do not mutate the database in check mode.
- Do not connect to external databases without explicit env.

## Evidence

Evidence lives under `artifacts/slices/090-host-schema-check-mode/090.1/`.
