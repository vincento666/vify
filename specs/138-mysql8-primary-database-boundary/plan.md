# Plan

1. Add a focused RED suite for database URL defaults, Alembic defaults, product
   demo docs, and app/script SQLite URL scans.
2. Introduce a central database URL policy for MySQL8-only validation.
3. Wire the policy into `Settings`, `make_engine`, and Alembic.
4. Remove product demo UAT instructions that seed or serve against SQLite.
5. Harden live acceptance so it requires a MySQL8 `HIFY_DATABASE_URL` instead of
   creating a temporary SQLite database.
6. Run focused and full unit gates against a real MySQL8 URL.
7. Continue with MySQL8 persistence, seed, frontend, and browser UAT gates.

## Test Strategy

- RED: `rtk env PYTHONPATH=. uv run pytest tests/unit/core/test_mysql8_database_boundary.py -q`.
- Focused unit: `rtk env PYTHONPATH=. uv run pytest tests/unit/core tests/unit/customer_assistant/test_live_react_acceptance_gate.py -q`.
- Full unit: `rtk env PYTHONPATH=. HIFY_DATABASE_URL=mysql+pymysql://... uv run pytest tests/unit -q`.
- MySQL8 opt-in: `rtk env PYTHONPATH=. HIFY_MYSQL8_TEST_DATABASE_URL=mysql+pymysql://... uv run pytest -rs tests/integration/mysql8`.
- Browser UAT: seed and run `scripts/dev.sh` with the same MySQL8 URL.

## Risks

- Local port `3306` may belong to a non-Hify MySQL instance. Gate commands must
  explicitly set the Hify MySQL8 URL when the default port is not the active
  demo database.
- Existing tests that bypass app database factories with direct SQLAlchemy
  engines may still exercise SQLite as pure dialect tests; those are not valid
  product MVP evidence.
