# Spec 182: Final Backend Non-Live Gate Revalidation

## Status

Complete.

## Goal

Refresh the full non-live backend gate on the current branch after MySQL8,
frontend canvas, customer assistant, runtime v2, and demo UAT convergence.
This slice proves the local test matrix remains green without calling live LLM
providers.

## Functional Requirements

- Run backend unit, integration, contract, and e2e suites.
- Run the acceptance suite in default non-live mode to prove live tests skip
  unless explicitly enabled.
- Run MySQL8-only boundary and focused MySQL8 write compatibility gates.
- Save outputs under
  `artifacts/slices/182-final-backend-nonlive-gate-revalidation/182.1/`.

## Non-Goals

- Do not run OpenRouter or other live provider calls in this slice.
- Do not modify product code unless a gate exposes a regression.
- Do not weaken skips or test assertions.

## Acceptance Criteria

- [x] Unit/integration/contract/e2e backend tests pass.
- [x] Acceptance suite default path passes with explicit live skips.
- [x] MySQL8-only boundary remains green.
- [x] Artifact scan finds no OpenRouter key material and no SQLite database
  URLs.

## Evidence

Evidence is saved under
`artifacts/slices/182-final-backend-nonlive-gate-revalidation/182.1/`.

### RED

- `unit.txt` failed because the unwrapped run reached the default
  `127.0.0.1:3306` MySQL URL and exposed a host/check startup mode regression.
- `contract.txt` and `acceptance-default.txt` failed for the same unwrapped
  default MySQL8 test database boundary.
- `integration-mysql8.txt` failed once under MySQL8 because the host `.env`
  contained demo `HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS` values pointing at
  Chatflow ids that do not exist in a disposable empty test database.
- `integration-runtime-lab-reliability-isolated.txt` captured the focused
  failing Runtime Lab idempotency case before the `.env` binding was isolated.

### GREEN

All final backend gates were run with explicit disposable MySQL8 databases and
`HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS=''` so the non-live suite does not inherit
host demo Chatflow ids.

- `unit-main-persistence-green.txt` passed after `app/main.py` restored
  lifespan startup checks to the module-level settings object.
- `unit-mysql8-isolated.txt` passed 308 tests.
- `integration-runtime-lab-reliability-green.txt` passed the focused Runtime
  Lab idempotency regression with host bindings cleared.
- `integration-mysql8-isolated.txt` passed 415 tests and skipped 6 live/vector
  opt-in tests.
- `contract-mysql8-isolated.txt` passed 56 tests.
- `e2e-mysql8-isolated.txt` passed 23 tests.
- `acceptance-default-mysql8-isolated.txt` passed 8 tests and skipped 8 live
  provider tests.
- `mysql8-boundary.txt` passed 13 MySQL8-only boundary tests.
- `mysql8-focused.txt` passed 3 focused MySQL8 persistence/write compatibility
  tests.
- `ruff.txt` passed for the touched startup file and related persistence-mode
  test.
- `artifact-scan.txt` is empty for OpenRouter key material, SQLite URL markers,
  `aiosqlite`, and historical `hify-uat.db` strings.

## Notes

This slice intentionally preserves the host `.env` demo binding file. The final
non-live gate now documents the required isolation: disposable database runs
must override `HIFY_DATABASE_URL` and clear runtime-lab demo Chatflow bindings
unless they seed matching Chatflows first.
