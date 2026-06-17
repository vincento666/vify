# Feature Spec: MySQL8 Unittest App Env Isolation

## Status

Complete.

## User Story

As a maintainer running productized MVP gates, I can run FastAPI TestClient
integration tests with only the MySQL8 test database settings, and the app
lifespan uses the same disposable MySQL8 schema as the test session instead of
falling back to an old default database URL.

## Functional Requirements

- `mysql8_unittest_database()` must set `HIFY_DATABASE_URL` to the disposable
  test database URL for the lifetime of the unittest case.
- The helper must restore the previous `HIFY_DATABASE_URL` value and clear the
  settings cache during cleanup.
- FastAPI startup must evaluate current settings at lifespan entry instead of a
  stale import-time settings object.
- The existing MySQL8 CREATE/DROP isolation remains mandatory; no shared-schema
  fallback and no SQLite fallback are allowed.

## Non-Goals

- No production database URL change.
- No new database tables or migrations.
- No frontend changes.
- No change to live acceptance provider configuration.

## Acceptance Criteria

- RED evidence shows `tests/integration/customer_assistant/test_worker_profiles.py`
  fails when only `HIFY_MYSQL8_TEST_DATABASE_URL` and
  `HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL` are provided, because TestClient startup
  still targets the stale/default app database.
- RED helper test fails before implementation because `mysql8_unittest_database`
  does not configure `HIFY_DATABASE_URL` to the disposable schema.
- After implementation, the helper test and worker profile integration suite pass
  with MySQL8 test/admin URLs and without an explicit external
  `HIFY_DATABASE_URL`.
- Focused ruff passes for touched files.

## Evidence

Evidence lives under
`artifacts/slices/151-mysql8-unittest-app-env-isolation/151.1/`.

- RED worker profiles: `red-worker-profiles.txt`
- RED helper: `red-helper.txt`
- Helper integration: `helper.txt`
- Worker profiles integration: `worker-profiles.txt`
- Ruff: `ruff.txt`
