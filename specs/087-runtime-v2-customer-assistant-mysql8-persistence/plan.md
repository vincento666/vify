# Plan 087

## 087.1 Persistence Smoke Gate

- Capture RED evidence that the focused MySQL8 runtime/customer-assistant gate
  does not exist yet.
- Add a MySQL8 integration test that creates only the needed tables and writes
  deterministic nested JSON payloads with unique test keys.
- Assert representative uniqueness/idempotency constraints through real MySQL
  duplicate-key errors.
- Document the new focused gate in the MySQL8 + Weaviate demo guide.

## Gates

- RED: missing regression gate before adding the test.
- Green: `tests/integration/mysql8/test_mysql8_runtime_v2_customer_assistant_persistence.py`
  against real MySQL8 when `HIFY_MYSQL8_TEST_DATABASE_URL` is set.
- Fallback environment evidence: skipped MySQL8 test when the URL is absent.
- Ruff for touched docs/test files.
- Browser UAT is not applicable because this slice changes persistence coverage
  only.
