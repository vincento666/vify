# 129 Plan

1. Add RED coverage to the one-click demo seed integration test requiring the
   persistence fingerprint.
2. Add an opt-in MySQL8 one-click seed command test guarded by
   `HIFY_MYSQL8_TEST_DATABASE_URL`.
3. Extend the seed report writer with sanitized persistence metadata derived
   from the active SQLAlchemy bind.
4. Run focused integration tests, the MySQL8 opt-in target, and Ruff.

## Commands

```bash
rtk uv run pytest tests/integration/customer_assistant/test_one_click_demo_seed.py::OneClickDemoSeedTest::test_one_click_seed_is_idempotent_and_writes_report_manifest
rtk env PYTHONPATH=. uv run pytest -rs tests/integration/mysql8/test_mysql8_one_click_demo_seed.py
rtk uv run ruff check app/modules/demo/mvp_seed.py tests/integration/customer_assistant/test_one_click_demo_seed.py tests/integration/mysql8/test_mysql8_one_click_demo_seed.py
```

