# 007.5 Browser UAT

- Date: 2026-05-31
- Slice: 007.5 Safety/failure behavior
- URL: http://127.0.0.1:5193/chat
- Screenshot: `output/playwright/0075-workflow-error.png`

## Flow

1. Created a workflow with nodes but no `START` node.
2. Created a workflow-bound Agent and chat session.
3. Opened the Chat page in a browser.
4. Sent `hello`.

## Expected Result

- The assistant stream contains `Workflow error: Workflow START node not found`.
- API tests verify failed runs are recorded as `FAILED`.

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
