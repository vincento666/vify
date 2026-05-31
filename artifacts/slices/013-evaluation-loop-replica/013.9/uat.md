# 013.9 Browser UAT: Selected Case Rerun

Date: 2026-06-01

## Scope

- Open a failed run report from Run Records.
- Trigger rerun for a selected failed case.
- Verify a new one-case run is created and the report updates to the rerun result.

## Evidence

- Screenshot: `case-rerun.png`
- E2E log: `e2e.txt`
- Backend suite: `backend-evaluation-suite.txt`
- Frontend unit suite: `frontend-unit.txt`
- Frontend build: `frontend-build.txt`
- Red tests: `red-backend.txt`, `red-frontend.txt`

## Result

PASS. Selected case rerun preserves the original run history, creates a new single-case run from the selected case, reruns the target through the current experiment configuration, and displays the refreshed report in the browser.
