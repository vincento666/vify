# Spec 179: MVP Demo Story Browser UAT MySQL8 Rerun

## Status

Slice 179.1 complete.

## Goal

Refresh the productized MVP demo story browser UAT with a real MySQL8-backed
seed and dev server. Slice 115 originally proved the workbench story line, but
the current completion path requires the same browser UAT evidence to come from
MySQL8, not stale local artifact notes.

## Functional Requirements

- Create a disposable MySQL8 UAT schema.
- Run `scripts/seed_one_click_mvp_demo.py` against that schema.
- Start `scripts/dev.sh` with the same MySQL8 schema and dedicated ports.
- Run `frontend/e2e/customer-assistant-real-seeded-mvp-demo-story-browser-uat.mjs`
  against the live Vite/FastAPI stack.
- Save seed, dev-server, browser UAT, report, notes, screenshots, and
  no-SQLite scan evidence under
  `artifacts/slices/179-mvp-demo-story-browser-uat-mysql8-rerun/179.1/`.

## Non-Goals

- Do not change production frontend/backend code unless the UAT exposes a real
  blocker.
- Do not use route mocks.
- Do not require live LLM provider calls.

## Acceptance Criteria

- RED evidence records that the MySQL8 rerun artifact did not exist before this
  slice.
- Seed command succeeds with a `mysql+pymysql://...` `HIFY_DATABASE_URL`.
- Dev server readiness probes succeed on the chosen ports with the same
  MySQL8 database URL.
- Browser UAT verifies the three seeded stories, operator Q&A, worker profile
  panel, metrics/eval panels, and one confirm path.
- Final scan over the 179.1 artifact directory finds no SQLite markers.
- Focused MySQL8 boundary tests pass.

## Evidence

Evidence lives under
`artifacts/slices/179-mvp-demo-story-browser-uat-mysql8-rerun/179.1/`.

- RED: `red.txt`
- Seed: `seed.txt`
- Dev server: `dev-server.txt`
- Browser UAT: `uat.txt`
- Browser report: `uat-report.json`
- UAT notes: `uat.md`
- Screenshots: `screenshots/`
- Report check: `report-check.txt`
- Scans: `no-sqlite-scan.txt`, `secret-scan.txt`
- MySQL8 boundary: `mysql8-boundary.txt`
