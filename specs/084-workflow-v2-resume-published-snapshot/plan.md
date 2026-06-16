# Plan 084

## 084.1 Workflow V2 Resume Snapshot Immutability

- Add a RED public-API integration test that starts a published Workflow v2 run,
  interrupts on `QUESTION`, edits the draft `MESSAGE`, and resumes the run.
- Fix runtime v2 resume to reuse the persisted runtime definition from the
  started run input.
- Run the focused integration test and runtime v2 unit checks.

## Gates

- RED integration failure before implementation.
- Green focused integration test.
- Runtime v2 unit checks.
- Ruff for touched backend files.
