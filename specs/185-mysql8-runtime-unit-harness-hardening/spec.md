# Spec 185: MySQL8 Runtime Unit Harness Hardening

## Status

Slice 185.1 complete.

## Goal

Remove the remaining runtime/customer-adjacent unit-test SQLite database
fixtures so the MVP demo gate cannot regress into accidental SQLite coverage
after the MySQL8 migration.

## Functional Requirements

- Extend the MySQL8 boundary test to scan runtime, runtime-policy,
  customer-assistant, and workflow unit tests for SQLite database URLs.
- Migrate the offending unit tests to the existing disposable MySQL8 test
  harness.
- Keep the dedicated core tests that assert SQLite is rejected.
- Save RED/GREEN evidence under
  `artifacts/slices/185-mysql8-runtime-unit-harness-hardening/185.1/`.

## Non-Goals

- Do not change product runtime behavior.
- Do not touch AI Assistant harness work.
- Do not broaden the scan to core compatibility tests that intentionally create
  synthetic non-runtime engines.

## Acceptance Criteria

- RED evidence shows the stricter runtime-unit scan failing on existing SQLite
  unit fixtures.
- The migrated unit tests pass using disposable MySQL8 databases.
- The focused MySQL8 boundary gate passes.
- The final scan over runtime/customer/workflow unit tests finds no SQLite URL
  fixtures outside the core rejection tests.

## Evidence

Evidence lives under
`artifacts/slices/185-mysql8-runtime-unit-harness-hardening/185.1/`.

- RED: `red.txt` fails on four SQLite unit fixtures:
  `runtime_lab_web_factory`, `runtime_policy/test_runtime_factories`,
  `runtime_policy/test_release_service`, and `runtime_policy/test_resolver`.
- Focused unit: `focused-unit.txt` passes 17 migrated runtime-lab/runtime-policy
  unit tests against explicit disposable MySQL8 test/admin URLs.
- Boundary: `mysql8-boundary.txt` passes 14 MySQL8 boundary tests and 2
  subtests.
- Scan: `unit-sqlite-scan.txt` is empty for runtime/customer/workflow unit
  SQLite URL markers.
- Ruff: `ruff.txt` passes for the touched tests.
