# Slice 193.13 Gates

## Unit

- `rtk uv run pytest tests/unit/ai_assistant/test_qwen_live_planner.py -q`
  - Result: `4 passed`
- `rtk npm --prefix frontend run test:unit -- src/views/aiAssistant/aiAssistantTimeline.test.ts`
  - Result: `7 passed`
- `rtk npm --prefix frontend run test:unit -- src/views/aiAssistant/aiAssistantShell.test.ts`
  - Result: `17 passed`

## Frontend Rem And Build

- `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`
  - Result: `1 passed`
- `rtk npm --prefix frontend run test:unit`
  - Result: `403 passed`
- `rtk npm --prefix frontend run build`
  - Result: passed with existing Vite chunk-size warning.

## Backend Live Gate

- `rtk env OPENROUTER_API_KEY=<redacted> uv run pytest tests/e2e/test_ai_assistant_live_qwen_openrouter_e2e.py -q`
  - Result: `1 passed`

## Backend AI Assistant Gate

- AI Assistant unit, integration, contract, and e2e suite against MySQL8.
  - Result before duration slice: `40 passed`

## Remaining Risk

- No provider secret is persisted or committed.
- Browser UAT uses a temporary OpenRouter key configured in the page only.
