# 005.5 RAG/Workflow Hook UAT

Date: 2026-05-31

## Scope

- Open the real frontend `/chat` page.
- Create a session with a workflow-bound Agent and verify `Workflow mock` response.
- Create a session with a knowledge-base-bound Agent and verify `RAG mock` response.
- Verify both sessions appear in the sidebar with their latest mock previews.

## Seed Data

- Agent: `UAT Workflow Agent 0055`
- Agent: `UAT RAG Agent 0055`
- Knowledge base: `UAT KB 0055`
- Workflow: `UAT Workflow 0055`

## Result

- Browser UAT: passed.
- Workflow response: `Workflow mock: workflow please`
- RAG response: `RAG mock: rag please`
- Screenshot: `output/playwright/0055-chat-bound-hooks.png`

## Gate Evidence

- RED: `artifacts/slices/005-chat-engine/005.5/red.txt`
- Focused backend tests: `artifacts/slices/005-chat-engine/005.5/backend.txt`
- Ruff: `artifacts/slices/005-chat-engine/005.5/ruff.txt`
- Mypy: `artifacts/slices/005-chat-engine/005.5/mypy.txt`
- Frontend unit: `artifacts/slices/005-chat-engine/005.5/frontend-unit.txt`
- Frontend build: `artifacts/slices/005-chat-engine/005.5/frontend-build.txt`
