# Plan: Customer Assistant Test DB Isolation

## Slice 128.1

Make demo seed integration tests restore process-level database environment
before their temporary SQLite directory is removed.

## Approach

1. Capture the current failing combined test command as RED evidence.
2. Add a restore helper in the demo bootstrap contract test and use it for the
   subprocess-backed seed test.
3. Ensure context managers restore `HIFY_DATABASE_URL` and clear settings cache
   before cleaning temporary directories.
4. Run the focused combined test, then the customer-assistant integration suite.

## Test Strategy

- Focused failing/passing command:
  - `tests/integration/customer_assistant/test_mvp_demo_bootstrap_contract.py`
  - `tests/integration/customer_assistant/test_worker_profiles.py`
- Full local integration probe:
  - `tests/integration/customer_assistant`

## Risks

- Some tests use app dependency overrides and some use environment-backed
  settings; fixes must avoid changing app behavior outside tests.
