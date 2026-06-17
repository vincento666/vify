# Plan: 151.1 MySQL8 Unittest App Env Isolation

## Slice

Make MySQL8 unittest-backed FastAPI tests self-contained: the disposable DB
helper configures the app database URL for the test lifetime.

1. Capture current RED worker profile integration failure with only
   `HIFY_MYSQL8_TEST_DATABASE_URL` and admin URL.
2. Add a focused RED helper test proving `mysql8_unittest_database` should set
   `HIFY_DATABASE_URL` to its disposable schema and restore it on cleanup.
3. Update the helper to use the existing database URL override semantics.
4. Update app startup to read current settings inside lifespan.
5. Run helper, worker profile integration, and focused ruff gates.

## Verification

- `rtk env PYTHONPATH=. HIFY_MYSQL8_TEST_DATABASE_URL=... HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL=... uv run pytest tests/integration/test_mysql8_unittest_app_env_isolation.py`
- `rtk env PYTHONPATH=. HIFY_MYSQL8_TEST_DATABASE_URL=... HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL=... uv run pytest tests/integration/customer_assistant/test_worker_profiles.py`
- `rtk env PYTHONPATH=. uv run ruff check app/main.py tests/support/mysql.py tests/integration/test_mysql8_unittest_app_env_isolation.py`

## Result

Completed. Final evidence is saved under
`artifacts/slices/151-mysql8-unittest-app-env-isolation/151.1/`.
