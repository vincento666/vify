# Plan

1. Create the 115 SDD slice and evidence directory.
2. Capture RED by running the planned browser UAT before the script exists.
3. Add a focused `frontend/e2e/customer-assistant-*` Playwright script that
   uses real backend data and writes a structured report.
4. Run the one-click seed against a fresh SQLite UAT database, then run
   `scripts/dev.sh` with the same database.
5. Run the browser UAT against the dev server, capture screenshots/report, and
   stop the dev server.
6. Update slice evidence docs and commit the tracked spec, script, and evidence
   summary if all gates pass.

## Test Strategy

- RED: missing browser script evidence.
- Seed: `env PYTHONPATH=. HIFY_DATABASE_URL=sqlite:///... uv run python scripts/seed_one_click_mvp_demo.py`.
- Browser UAT: `node frontend/e2e/customer-assistant-real-seeded-mvp-demo-story-browser-uat.mjs`.
- Frontend unit/rem: not required unless production frontend code changes.

## Risks

- Shared default dev database state can make confirm paths non-repeatable, so
  115 uses a fresh artifact SQLite database for seed and dev server.
- The UAT confirms one seeded pending action, so it should be run after seed in
  the same isolated database.
