# Spec 138: MySQL8 Primary Database Boundary

## Status

Complete.

## Goal

Make MySQL8 the only supported application runtime database for the
productized MVP demo so default configuration, migrations, live gates, and
browser UAT cannot drift back to SQLite.

## Functional Requirements

- Default `Settings.database_url` must be a MySQL8 URL.
- `Settings` must reject `HIFY_DATABASE_URL` values that are SQLite or any
  non-MySQL backend.
- `app.core.database.make_engine` must reject SQLite and non-MySQL URLs even if
  callers bypass `Settings`.
- Alembic must default to MySQL8 and must still honor an explicit
  `HIFY_DATABASE_URL` override.
- Product demo evidence and plans must not instruct seed, dev server, or UAT
  runs to use SQLite.
- Live LLM acceptance gates must require an explicit MySQL8 `HIFY_DATABASE_URL`
  before they execute runtime persistence paths.

## Non-Goals

- Removing SQLAlchemy dialect-compatibility unit tests that compile or inspect
  in-memory SQLite schemas without using application runtime configuration.
- Replacing the existing MySQL8 docker topology.
- Changing provider, worker, Chatflow, or customer-assistant business behavior.

## Acceptance Criteria

- RED focused test proves the old defaults allowed SQLite in Settings, Alembic,
  and product demo evidence.
- RED static scan proves application code still had a SQLite live-gate fallback.
- Focused MySQL8 boundary unit tests pass.
- Full unit suite passes with `HIFY_DATABASE_URL` pointed at a real MySQL8
  database.
- MySQL8 persistence and one-click seed gates pass or fail with explicit MySQL8
  connectivity evidence.
- Browser UAT uses the MySQL8 database URL, not SQLite.

## Evidence

Evidence is saved under `artifacts/slices/138-mysql8-primary-database-boundary/`
or the root ignored artifact files with the same prefix.

- RED: `138-mysql8-primary-database-boundary-red.txt`
- App scan RED: `138-mysql8-primary-database-boundary-app-scan-red.txt`
- Focused unit: `138-mysql8-primary-database-boundary-unit-focused-2.txt`
- Full unit with MySQL8: `138-mysql8-primary-database-boundary-unit-full-mysql8-2.txt`
- MySQL8 integration: `138-mysql8-primary-database-boundary-mysql8-integration-3.txt`
- Ruff: `138-mysql8-primary-database-boundary-ruff.txt`
- One-click seed: `138-mysql8-primary-database-boundary-one-click-seed.txt`
- Workflow tabs browser smoke: `138-mysql8-primary-database-boundary-frontend-e2e-workflow-tabs-3.txt`
- 071 canvas browser UAT: `138-mysql8-primary-database-boundary-071-canvas-uat.txt`
- MVP demo browser UAT: `138-mysql8-primary-database-boundary-browser-uat-115.txt`
- Frontend rem: `138-mysql8-primary-database-boundary-frontend-rem.txt`
- Frontend unit: `138-mysql8-primary-database-boundary-frontend-unit-full.txt`
- Frontend build: `138-mysql8-primary-database-boundary-frontend-build.txt`
