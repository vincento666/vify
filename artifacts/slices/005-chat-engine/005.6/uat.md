# 005.6 Tool-Call Boundary UAT

Date: 2026-05-31

## Scope

- Open the real frontend `/chat` page.
- Create a session with an Agent bound to an MCP server.
- Send a message containing `tool`.
- Verify the visible assistant response and persisted history use the mock tool fallback path.

## Seed Data

- Agent: `UAT Tool Agent 0056`
- MCP server: `UAT MCP Tool 0056`

## Result

- Browser UAT: passed.
- User message: `please use tool`
- Assistant message: `Tool mock: please use tool`
- Screenshot: `output/playwright/0056-chat-tool-fallback.png`

## Gate Evidence

- RED: `artifacts/slices/005-chat-engine/005.6/red.txt`
- Focused backend tests: `artifacts/slices/005-chat-engine/005.6/backend.txt`
- Ruff: `artifacts/slices/005-chat-engine/005.6/ruff.txt`
- Mypy: `artifacts/slices/005-chat-engine/005.6/mypy.txt`
- Frontend unit: `artifacts/slices/005-chat-engine/005.6/frontend-unit.txt`
- Frontend build: `artifacts/slices/005-chat-engine/005.6/frontend-build.txt`
