# MVP Demo Story Browser UAT Evidence

Spec: `specs/115-mvp-demo-story-browser-uat`

## Status

Complete, superseded by the MySQL8-only database boundary in slice 138.

## Evidence Index

Runtime evidence is saved outside git under
`artifacts/slices/115-mvp-demo-story-browser-uat/115.1/`.

- RED: `red.txt`
- Seed: `seed.txt`
- Dev server: `dev-server.txt`
- Browser UAT: `uat.txt`
- Report: `uat-report.json`
- Notes: `uat.md`
- Screenshots: `screenshots/`

## Commands

Seed:

```bash
rtk env PYTHONPATH=. HIFY_DATABASE_URL=mysql+pymysql://hify:hify@127.0.0.1:3306/hify?charset=utf8mb4 HIFY_ONE_CLICK_DEMO_ENV_PATH=/Users/vincento/work/develop/hify/artifacts/slices/115-mvp-demo-story-browser-uat/115.1/.env.demo HIFY_ONE_CLICK_DEMO_REPORT_PATH=/Users/vincento/work/develop/hify/artifacts/slices/115-mvp-demo-story-browser-uat/115.1/one-click-seed-report.json uv run python scripts/seed_one_click_mvp_demo.py
```

Dev server:

```bash
rtk env PYTHONPATH=. HIFY_DATABASE_URL=mysql+pymysql://hify:hify@127.0.0.1:3306/hify?charset=utf8mb4 HIFY_BACKEND_PORT=18080 HIFY_FRONTEND_PORT=15173 scripts/dev.sh
```

Browser UAT:

```bash
rtk env HIFY_E2E_BASE_URL=http://127.0.0.1:15173 HIFY_E2E_ARTIFACT_DIR=/Users/vincento/work/develop/hify/artifacts/slices/115-mvp-demo-story-browser-uat/115.1 node frontend/e2e/customer-assistant-real-seeded-mvp-demo-story-browser-uat.mjs
```

## UAT Result

- Seed result: three demo stories, sessions `1,2,3`, provider/model config `1`,
  knowledge base `1`, and 15 Chatflow SOP bindings.
- Browser result: `PASS customer assistant real seeded mvp demo story browser uat`.
- Verified stories:
  `invoice_interrupt_flight_status`,
  `refund_baggage_parallel`,
  `chatflow_block_resume_recommendation`.
- Verified panels:
  story picker/deeplink, customer conversation, task ledger, proposed actions,
  worker profile config, operator knowledge Q&A, metrics, and
  eval/observability.
- Confirm path:
  generated and confirmed `取消任务：refund_ticket:MU5137-8899`.
- Screenshots:
  `/Users/vincento/work/develop/hify/artifacts/slices/115-mvp-demo-story-browser-uat/115.1/screenshots/invoice-deeplink-story.png`,
  `/Users/vincento/work/develop/hify/artifacts/slices/115-mvp-demo-story-browser-uat/115.1/screenshots/refund-qa-confirmed.png`,
  `/Users/vincento/work/develop/hify/artifacts/slices/115-mvp-demo-story-browser-uat/115.1/screenshots/chatflow-resume-story.png`.

## Integration Notes

- The UAT now uses MySQL8 only. For repeatable local runs, point
  `HIFY_DATABASE_URL` at a disposable MySQL8 schema and reset that schema before
  seeding.
- The browser script must use the real FastAPI backend and Vite frontend started
  by `scripts/dev.sh`; route mocks are not part of the primary evidence.
- After shutdown, port `15173` refused connections. Port `18080` was held by an
  existing OrbStack listener returning its own 404, not the Hify health payload.
- Visual spot-check: the existing long Chatflow story title wraps awkwardly in
  the story card, but selection and required panel evidence remained usable.
