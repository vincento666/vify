# 013.8 Browser UAT: Workflow and Chatflow Evaluation Targets

Date: 2026-06-01

## Scope

- Create a Workflow-backed evaluation experiment from the Evaluation workbench.
- Create a Chatflow-backed evaluation experiment from the same flow.
- Verify both target types execute through the existing graph engine and produce completed runs.

## Evidence

- Screenshot: `workflow-chatflow-targets.png`
- E2E log: `e2e.txt`
- Backend suite: `backend-evaluation-suite.txt`
- Frontend unit suite: `frontend-unit.txt`
- Frontend build: `frontend-build.txt`
- Red tests: `red-backend.txt`, `red-frontend.txt`

## Result

PASS. Evaluation experiments now accept Agent, Workflow, and Chatflow targets. Workflow and Chatflow targets are validated by `flow_type`, run through the existing workflow facade, and surface completed run summaries in the browser.
