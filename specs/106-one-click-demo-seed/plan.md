# Plan 106

## 106.1 Mock-Safe One-Click Seed Command

- Add a RED integration test for a reusable one-click seed helper and script.
- Extend the existing MVP demo seed with idempotent mock provider/model config
  anchors.
- Add `seed_one_click_mvp_demo(...)` to seed, write env bindings, verify the
  topology, and optionally write a JSON report.
- Add `scripts/seed_one_click_mvp_demo.py` as the user-facing one-command
  entrypoint.
- Save RED and green focused evidence, then commit the slice.

## Gates

- Focused integration test for the 106 helper and command.
- Existing 073 seed integration remains green.
- Existing 079 bootstrap contract remains green.
- Ruff on touched Python files.
- Browser UAT is not required because this slice does not touch user-visible
  frontend files.
