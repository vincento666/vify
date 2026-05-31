# 007.4 Browser UAT

- Date: 2026-05-31
- Slice: 007.4 Condition branching
- URL: http://127.0.0.1:5193/chat
- Screenshot: `output/playwright/0074-condition-chat.png`

## Flow

1. Seeded a model config for the test Agent.
2. Created a conditional workflow through the running API.
3. Created a workflow-bound Agent and chat session.
4. Opened the Chat page in a browser.
5. Sent `vip`.
6. Sent `unknown`.

## Expected Result

- `vip` produces `Workflow mock: LLM mock: VIP branch`.
- `unknown` produces `Workflow mock: LLM mock: Default branch`.

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
