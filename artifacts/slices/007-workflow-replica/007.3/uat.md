# 007.3 Browser UAT

- Date: 2026-05-31
- Slice: 007.3 Linear execution
- URL: http://127.0.0.1:5193/chat
- Screenshot: `output/playwright/0073-workflow-chat.png`

## Flow

1. Seeded a model config for the test Agent.
2. Created a linear workflow through the running API:
   `START -> LLM -> END`.
3. Created a workflow-bound Agent and chat session.
4. Opened the Chat page in a browser.
5. Sent `reset password`.

## Expected Result

- The assistant stream contains `Workflow mock: LLM mock: User: reset password`.
- The workflow run and node runs are recorded by integration tests.

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
