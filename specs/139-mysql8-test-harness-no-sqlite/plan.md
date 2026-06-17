# Plan

## Status

Complete. The harness now refuses shared-schema fallback, requires disposable
MySQL8 database creation, and uses `HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL` when
the app user does not own database-level create/drop privileges.

## Slice 139.1 Static Gate

Add a red test that scans runtime-adjacent test suites for SQLite URL and driver
usage. This fails on the current tree and becomes the regression guard.

## Slice 139.2 Shared MySQL8 Harness

Introduce `tests.support.mysql` helpers that:

- validate the base URL as MySQL8,
- create a unique disposable database,
- use `HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL` for create/drop/grant when the
  normal test user does not own database-level privileges,
- fail fast instead of reusing a shared schema when disposable database creation
  is unavailable,
- expose a SQLAlchemy engine or `HIFY_DATABASE_URL` context,
- initialize the app schema using the existing MySQL-aware schema filter,
- drop the database on exit and restore settings cache.

## Slice 139.3 Seed And Bootstrap Migration

Migrate one-click demo seed, MVP demo seed, bootstrap contract, and RuntimeLab
airline seed tests from SQLite temp files to the shared MySQL8 harness.

## Slice 139.4 Integration And Contract Sweep

Replace direct SQLite engines in runtime-adjacent integration, contract, e2e, and
acceptance tests with the shared harness. Preserve behavior-level assertions.

## Slice 139.5 Gates

Run focused red/green, full backend integration+contract, existing MySQL8 gates,
frontend non-visual gates where relevant, and update evidence/tasks.
