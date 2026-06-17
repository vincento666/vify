# Plan

1. Add SDD docs for the 115 artifact convergence guard.
2. Add a RED unit test to extend the MySQL8 database boundary over current 115
   browser UAT artifacts.
3. Update the local 115.1 seed and dev-server evidence text to MySQL8-only
   commands and notes.
4. Remove stale local SQLite database artifacts from 115.1.
5. Replace tracked product demo/live acceptance spec wording that still
   prescribes SQLite runtime databases.
6. Run focused boundary tests and a final no-SQLite scan over the 115.1
   artifact directory.
7. Record evidence under
   `artifacts/slices/157-mvp-demo-uat-artifact-mysql8-convergence/157.1/` and
   commit the tracked guard.

## Test Strategy

- RED: `tests/unit/core/test_mysql8_database_boundary.py::Mysql8DatabaseBoundaryTest::test_product_demo_uat_artifacts_do_not_retain_sqlite_evidence`.
- Unit: `tests/unit/core/test_mysql8_database_boundary.py`.
- Scan: `rg -n "sqlite|SQLite|hify-uat\\.db" artifacts/slices/115-mvp-demo-story-browser-uat/115.1`.
