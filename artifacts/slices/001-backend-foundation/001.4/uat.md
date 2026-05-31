# UAT 001.4: Alembic baseline schema

Status: PASS

Browser check:

- URL: `file:///Users/vincento/work/develop/hify/artifacts/slices/001-backend-foundation/001.4/schema-report.html`
- Browser command: `npx playwright screenshot --browser chromium --full-page --viewport-size=1280,720`
- Screenshot: `screenshots/schema-report.png`

Expected user-visible result:

- Schema report displays all baseline tables from spec 000.
- `agent` includes `knowledge_base_id` and `workflow_id`.

Evidence:

- RED: `red.txt` fails before `app.core.database` and Alembic script folder exist.
- Unit: `unit.txt` passes metadata superset checks.
- Integration: `alembic-test.txt` passes Alembic upgrade in a temporary SQLite database.
- E2E: `e2e.txt` passes `uv run alembic upgrade head` with `HIFY_DATABASE_URL`.
- DB inspect: `schema-inspect.txt` lists the created tables and augmented `agent` columns.
- Browser UAT: `browser-uat.txt` captures the schema report through Chromium.
