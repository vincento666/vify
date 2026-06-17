# Plan

1. Add SDD docs for live LLM artifact MySQL8 convergence.
2. Add RED unit coverage over current 135/136 live artifact directories.
3. Rewrite stale local artifact notes to MySQL8-only wording.
4. Run focused boundary tests and final artifact scan.
5. Save evidence under
   `artifacts/slices/178-live-llm-artifact-mysql8-convergence/178.1/` and
   commit the tracked guard.

## Test Strategy

- Unit: `tests/unit/core/test_mysql8_database_boundary.py`.
- Scan: `rg -n "disposable SQLite|SQLite database|sqlite://|hify\\.db|hify-uat\\.db" artifacts/slices/135-* artifacts/slices/136-*`.

