# Spec 115: MVP Demo Story Browser UAT

## Status

Slice 115.1 complete.

## Goal

Prove that the productized MVP demo is repeatable through the real one-click
seed, the real dev server, and the customer-assistant workbench. The evidence
must cover two to three seeded demo stories without route mocks.

## Functional Requirements

- Run `scripts/seed_one_click_mvp_demo.py` against a deterministic UAT database
  before browser verification.
- Start the full local stack with `scripts/dev.sh` and use the customer
  assistant workbench at `/customer-assistant`.
- Verify seeded story discovery, direct story deeplink selection, and story
  switching while preserving unrelated query parameters.
- Verify visible customer conversation, task ledger, proposed actions, worker
  profile configuration, operator knowledge Q&A, and eval/observability panels.
- Verify at least one operator control path through an existing confirm or
  refresh action when the UI supports it.
- Save browser report JSON, green command output, UAT notes, and screenshots
  under `artifacts/slices/115-mvp-demo-story-browser-uat/115.1/`.

## Non-Goals

- Do not change production backend or frontend code unless a real UAT blocker
  prevents the demo and can be fixed narrowly.
- Do not use route mocks for the primary browser UAT.
- Do not require live LLM credentials or external provider calls.
- Do not replace the focused tests from specs 106, 109, 110, 112, 113, or 114.

## Acceptance Criteria

- RED evidence records the missing browser UAT script or failing UAT path before
  implementation.
- The seed command succeeds and writes its one-click report for the UAT
  database.
- The browser UAT script opens a seeded story by deeplink, switches to another
  seeded story, validates the required workbench panels, asks an operator
  knowledge question against the real backend, and confirms one available
  pending action.
- The UAT report includes verified story ids, panel evidence, confirmation
  evidence, and screenshot paths.
- The dev server is stopped after UAT.
- No focused frontend unit gate is required unless production frontend code is
  touched.

## Evidence

Evidence lives under
`artifacts/slices/115-mvp-demo-story-browser-uat/115.1/`.

- RED: `red.txt`
- Seed command: `seed.txt`
- Dev server log: `dev-server.txt`
- Browser UAT: `uat.txt`
- Browser report: `uat-report.json`
- UAT notes: `uat.md`
- Screenshots: `screenshots/`

## Result

The 115.1 browser UAT passed against a fresh SQLite database seeded by the
one-click demo command and served by `scripts/dev.sh`. The UAT verified all
three seeded story ids, direct deeplink selection, story switching, visible
conversation/task/action panels, worker profile configuration, operator
knowledge Q&A, eval/observability task evidence, and one confirmed task-control
path.
