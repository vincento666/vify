# 013.10 Browser UAT: Compare Analysis

Date: 2026-06-01

## Scope

- Compare a baseline run and candidate run from the Evaluation workbench.
- Verify score delta and pass-rate delta.
- Verify case buckets for newly failed, recovered, and unchanged failures.

## Evidence

- Screenshot: `compare-analysis.png`
- E2E log: `e2e.txt`
- Backend suite: `backend-evaluation-suite.txt`
- Frontend unit suite: `frontend-unit.txt`
- Frontend build: `frontend-build.txt`
- Red tests: `red-backend.txt`, `red-frontend.txt`

## Result

PASS. Compare Analysis is enabled in the workbench, calls the run comparison API, and displays score delta, pass-rate delta, newly failed cases, recovered cases, and unchanged failures.
