# Plan

1. Add SDD docs and capture RED missing-MySQL8-rerun evidence.
2. Allocate a disposable MySQL8 schema through the test DB helper.
3. Run one-click seed with `HIFY_DATABASE_URL` pointing at the disposable schema.
4. Start `scripts/dev.sh` on dedicated backend/frontend ports using the same
   schema, and capture readiness plus request evidence.
5. Run the real seeded browser UAT script with artifact outputs under `179.1`.
6. Stop the dev server, run no-SQLite/secret scans and focused MySQL8 boundary
   tests, then commit the tracked SDD and any required guard updates.

## Test Strategy

- RED: missing `uat-report.json` in `179.1`.
- Browser UAT:
  `frontend/e2e/customer-assistant-real-seeded-mvp-demo-story-browser-uat.mjs`.
- Boundary: `tests/unit/core/test_mysql8_database_boundary.py`.

