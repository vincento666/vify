# Plan

1. Create SDD docs and evidence directory.
2. Run the non-live backend pytest matrix by suite.
3. Run acceptance tests without live flags.
4. Run MySQL8-only and focused MySQL8 gates with explicit MySQL8 test URLs.
5. Scan artifacts for secret material and SQLite URL markers.
6. Update docs and commit tracked SDD.

All final non-live suite commands run with disposable MySQL8 databases and
`HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS=''` to prevent host `.env` demo Chatflow ids
from leaking into empty test databases.

## Test Strategy

- `uv run pytest tests/unit`
- `uv run pytest tests/integration`
- `uv run pytest tests/contract`
- `uv run pytest tests/e2e`
- `uv run pytest tests/acceptance` without live flags
- MySQL8:
  `tests/unit/core/test_mysql8_database_boundary.py`,
  `tests/integration/test_mysql8_unittest_app_env_isolation.py`,
  `tests/integration/mysql8/test_mysql8_one_click_demo_seed.py`,
  `tests/integration/mysql8/test_mysql8_repository_write_compat.py`
