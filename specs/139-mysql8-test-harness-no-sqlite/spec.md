# 139 MySQL8 Test Harness No SQLite

## Status

Complete.

## Goal

Productized MVP gates must not rely on SQLite anywhere in runtime-adjacent tests or
acceptance flows. Temporary databases for integration, contract, e2e, acceptance,
seed, and browser-UAT setup must be MySQL8 schemas created through a shared test
harness.

## Acceptance Criteria

- `tests/integration`, `tests/contract`, `tests/e2e`, and `tests/acceptance`
  contain no SQLite URL literals or direct SQLite engine setup.
- A shared MySQL8 test harness creates isolated disposable databases from
  `HIFY_MYSQL8_TEST_DATABASE_URL` or `HIFY_DATABASE_URL`.
- If the normal test user cannot create/drop databases, tests must provide
  `HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL`; the harness must refuse shared-schema
  fallback and must not `DROP TABLE` inside the application schema as a reset
  strategy.
- Seed/bootstrap tests run against MySQL8 and assert MySQL persistence
  fingerprints.
- RuntimeLab and customer-assistant integration and contract tests use the
  MySQL8 harness instead of per-test SQLite files.
- Full backend integration and contract gates run with MySQL8.
- Evidence is recorded under `artifacts/slices/139-mysql8-test-harness-no-sqlite/`.

## Non-Goals

- Reintroducing SQLite as a compatibility backend.
- Weakening MySQL8 validation or skipping tests when MySQL8 is available.

## Evidence

Evidence is saved under `artifacts/slices/139-mysql8-test-harness-no-sqlite*`.

- RED: static no-SQLite gate and connection validator failures.
- Unit: focused MySQL8 boundary and full unit suite.
- Integration/contract: full backend integration + contract with disposable
  MySQL8 databases.
- E2E/acceptance: customer-assistant runtime, SSE, and runtime policy flows.
- Live LLM: customer assistant and runtime v2 OpenRouter gates using
  `deepseek/deepseek-v4-flash`.
- Safety scans: final no-SQLite scan over runtime-adjacent suites and final
  OpenRouter key-prefix scan.
